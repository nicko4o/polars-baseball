from typing import Any

import polars as pl

from polars_baseball._schema_utils import validate_and_cast_schema
from polars_baseball._schemas.mlb import (
    MLB_PITCH_ARSENAL_REQUIRED,
    MLB_PITCH_ARSENAL_TYPES,
    MLB_PLAYER_STATS_REQUIRED,
    MLB_PLAYER_STATS_TYPES,
    MLB_STAT_LEADERS_REQUIRED,
    MLB_STAT_LEADERS_TYPES,
    MLB_TEAM_STATS_REQUIRED,
    MLB_TEAM_STATS_TYPES,
)
from polars_baseball.exceptions import UpstreamParseError
from polars_baseball.parsers.mlb.types import PitchArsenalDict, StatLeaderDict

_PITCH_ARSENAL_STATS_DISPLAY_NAME = "pitchArsenal"


def parse_player_stat_split(split: dict[str, Any], person_id: int, group: str, stat_type: str) -> dict[str, Any]:
    stat = split.get("stat", {})
    row = {
        "personId": person_id,
        "season": int(split["season"]) if split.get("season") else None,
        "group": group,
        "statType": stat_type,
    }
    for key, value in stat.items():
        if isinstance(value, dict):
            continue
        row[key] = value
    return row


def parse_player_stats(
    data: dict[str, Any],
    person_id: int,
    target_group: str,
    target_type: str,
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for stat_obj in data.get("stats", []):
        group = stat_obj.get("group", {}).get("displayName", target_group)
        stat_type = stat_obj.get("type", {}).get("displayName", target_type)
        for split in stat_obj.get("splits", []):
            rows.append(parse_player_stat_split(split, person_id, group, stat_type))
    return rows


def parse_team_stats(data: dict[str, Any], team_id: int, target_group: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for stat_obj in data.get("stats", []):
        group = stat_obj.get("group", {}).get("displayName", target_group)
        stat_type = stat_obj.get("type", {}).get("displayName", "season")
        for split in stat_obj.get("splits", []):
            stat = split.get("stat", {})
            row: dict[str, Any] = {
                "teamId": team_id,
                "season": int(split["season"]) if split.get("season") else None,
                "group": group,
                "statType": stat_type,
            }
            for key, value in stat.items():
                if isinstance(value, dict):
                    continue
                row[key] = value
            rows.append(row)
    return rows


def parse_leader(
    entry: dict[str, Any],
    category: str,
    season: int,
    stat_group: str | None,
) -> StatLeaderDict:
    person = entry.get("person", {})
    team = entry.get("team", {})
    league = entry.get("league", {})
    return {
        "rank": entry.get("rank"),
        "personId": person.get("id"),
        "personName": person.get("fullName"),
        "teamId": team.get("id"),
        "teamName": team.get("name"),
        "leagueId": league.get("id"),
        "category": category,
        "value": entry.get("value"),
        "season": season,
        "statGroup": stat_group,
    }


def parse_pitch_arsenal(split: dict[str, Any], person_id: int, season: int) -> PitchArsenalDict:
    if "stat" not in split:
        raise UpstreamParseError("Pitch arsenal entry missing 'stat' object")
    stat = split["stat"]
    if not isinstance(stat, dict):
        raise UpstreamParseError("Pitch arsenal 'stat' field is not a dictionary")

    pitch_type = stat.get("type") or stat.get("pitchType") or {}
    code = pitch_type.get("code")
    description = pitch_type.get("description")
    percentage = stat.get("percentage")
    average_speed = stat.get("averageSpeed")

    if code is None or description is None or percentage is None or average_speed is None:
        raise UpstreamParseError(
            f"Pitch arsenal missing core fields: code={code}, description={description}, "
            f"percentage={percentage}, averageSpeed={average_speed}"
        )

    return {
        "personId": person_id,
        "season": season,
        "pitchTypeCode": code,
        "pitchTypeName": description,
        "percentage": float(percentage),
        "averageSpeed": float(average_speed),
    }


def parse_mlb_player_stats(data: dict[str, Any], person_id: int, group: str, stats_type: str) -> pl.DataFrame:
    rows = parse_player_stats(data, person_id, group, stats_type)
    if not rows:
        return pl.DataFrame()
    return validate_and_cast_schema(pl.DataFrame(rows), MLB_PLAYER_STATS_REQUIRED, MLB_PLAYER_STATS_TYPES)


def parse_mlb_team_stats(data: dict[str, Any], team_id: int, group: str) -> pl.DataFrame:
    rows = parse_team_stats(data, team_id, group)
    if not rows:
        return pl.DataFrame()
    return validate_and_cast_schema(pl.DataFrame(rows), MLB_TEAM_STATS_REQUIRED, MLB_TEAM_STATS_TYPES)


def parse_mlb_stat_leaders(data: dict[str, Any], season: int, stat_group: str | None) -> pl.DataFrame:
    league_leaders = data.get("leagueLeaders", [])
    if not league_leaders:
        return pl.DataFrame()
    rows: list[StatLeaderDict] = []
    for leader_group in league_leaders:
        category = leader_group.get("leaderCategory", "unknown")
        for entry in leader_group.get("leaders", []):
            rows.append(parse_leader(entry, category, season, stat_group))
    if not rows:
        return pl.DataFrame()
    return validate_and_cast_schema(pl.DataFrame(rows), MLB_STAT_LEADERS_REQUIRED, MLB_STAT_LEADERS_TYPES)


def parse_mlb_pitch_arsenal(data: dict[str, Any], person_id: int, season: int) -> pl.DataFrame:
    stats = data.get("stats", [])
    rows: list[PitchArsenalDict] = []
    for stat in stats:
        if stat.get("type", {}).get("displayName") != _PITCH_ARSENAL_STATS_DISPLAY_NAME:
            continue
        splits = stat.get("splits", [])
        for split in splits:
            rows.append(parse_pitch_arsenal(split, person_id, season))
    if not rows:
        return pl.DataFrame()
    return validate_and_cast_schema(pl.DataFrame(rows), MLB_PITCH_ARSENAL_REQUIRED, MLB_PITCH_ARSENAL_TYPES)
