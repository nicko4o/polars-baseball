"""MLB Stats API parsers for player stats, team stats, stat leaders, and pitch arsenal."""

from typing import cast

import polars as pl

from polars_baseball._json_utils import JsonObject, safe_child_dict, to_float, to_int
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


def _iter_stat_splits(
    data: JsonObject,
    default_group: str,
    default_type: str,
) -> list[tuple[JsonObject, str, str]]:
    results: list[tuple[JsonObject, str, str]] = []
    stats = data.get("stats", [])
    if not isinstance(stats, list):
        return results
    for stat_obj in stats:
        if not isinstance(stat_obj, dict):
            continue
        group_dict = safe_child_dict(stat_obj, "group")
        type_dict = safe_child_dict(stat_obj, "type")
        group = str(group_dict.get("displayName") or default_group)
        stat_type = str(type_dict.get("displayName") or default_type)
        splits = stat_obj.get("splits", [])
        if not isinstance(splits, list):
            continue
        for split in splits:
            if isinstance(split, dict):
                results.append((cast(JsonObject, split), group, stat_type))
    return results


def parse_player_stat_split(split: JsonObject, person_id: int, group: str, stat_type: str) -> JsonObject:
    stat = safe_child_dict(split, "stat")
    row: JsonObject = {
        "personId": person_id,
        "season": to_int(split.get("season")),
        "group": group,
        "statType": stat_type,
    }
    for key, value in stat.items():
        if not isinstance(value, dict):
            row[key] = value
    return row


def parse_player_stats(
    data: JsonObject,
    person_id: int,
    target_group: str,
    target_type: str,
) -> list[JsonObject]:
    return [
        parse_player_stat_split(split, person_id, group, stat_type)
        for split, group, stat_type in _iter_stat_splits(data, target_group, target_type)
    ]


def _parse_team_split(split: JsonObject, team_id: int, group: str, stat_type: str) -> JsonObject:
    stat = safe_child_dict(split, "stat")
    row: JsonObject = {
        "teamId": team_id,
        "season": to_int(split.get("season")),
        "group": group,
        "statType": stat_type,
    }
    for key, value in stat.items():
        if not isinstance(value, dict):
            row[key] = value
    return row


def parse_team_stats(data: JsonObject, team_id: int, target_group: str) -> list[JsonObject]:
    return [
        _parse_team_split(split, team_id, group, stat_type)
        for split, group, stat_type in _iter_stat_splits(data, target_group, "season")
    ]


def parse_leader(
    entry: JsonObject,
    category: str,
    season: int,
    stat_group: str | None,
) -> StatLeaderDict:
    person = safe_child_dict(entry, "person")
    team = safe_child_dict(entry, "team")
    league = safe_child_dict(entry, "league")
    return cast(
        StatLeaderDict,
        {
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
        },
    )


def parse_pitch_arsenal(split: JsonObject, person_id: int, season: int) -> PitchArsenalDict:
    if "stat" not in split:
        raise UpstreamParseError("Pitch arsenal entry missing 'stat' object")
    stat = split["stat"]
    if not isinstance(stat, dict):
        raise UpstreamParseError("Pitch arsenal 'stat' field is not a dictionary")

    pitch_type_raw = stat.get("type") or stat.get("pitchType")
    pitch_type = pitch_type_raw if isinstance(pitch_type_raw, dict) else {}
    code = pitch_type.get("code")
    description = pitch_type.get("description")
    percentage = to_float(stat.get("percentage"))
    average_speed = to_float(stat.get("averageSpeed"))

    if code is None or description is None or percentage is None or average_speed is None:
        raise UpstreamParseError(
            f"Pitch arsenal missing core fields: code={code}, description={description}, "
            f"percentage={stat.get('percentage')}, averageSpeed={stat.get('averageSpeed')}"
        )

    return cast(
        PitchArsenalDict,
        {
            "personId": person_id,
            "season": season,
            "pitchTypeCode": code,
            "pitchTypeName": description,
            "percentage": percentage,
            "averageSpeed": average_speed,
        },
    )


def parse_mlb_player_stats(data: JsonObject, person_id: int, group: str, stats_type: str) -> pl.DataFrame:
    """Parse player stats from MLB Stats API /people/{id}/stats response.

    Flattens stats[].splits[].stat objects into rows, skipping nested
    dict values within each stat object. Each row is annotated with the
    person ID, season, group, and stat type.
    """
    rows = parse_player_stats(data, person_id, group, stats_type)
    if not rows:
        return pl.DataFrame()
    return validate_and_cast_schema(
        pl.DataFrame(rows, infer_schema_length=None), MLB_PLAYER_STATS_REQUIRED, MLB_PLAYER_STATS_TYPES
    )


def parse_mlb_team_stats(data: JsonObject, team_id: int, group: str) -> pl.DataFrame:
    """Parse team stats from MLB Stats API /teams/{id}/stats response.

    Flattens stats[].splits[].stat objects into rows, skipping nested
    dict values. Each row is annotated with the team ID, season, group,
    and stat type.
    """
    rows = parse_team_stats(data, team_id, group)
    if not rows:
        return pl.DataFrame()
    return validate_and_cast_schema(
        pl.DataFrame(rows, infer_schema_length=None), MLB_TEAM_STATS_REQUIRED, MLB_TEAM_STATS_TYPES
    )


def parse_mlb_stat_leaders(data: JsonObject, season: int, stat_group: str | None) -> pl.DataFrame:
    """Parse stat leaders from MLB Stats API /stats/leaders response.

    Iterates leagueLeaders[].leaderCategory entries and their nested
    leaders[] arrays. Each row captures the player, team, league,
    category, value, season, and stat group.
    """
    league_leaders = data.get("leagueLeaders", [])
    if not isinstance(league_leaders, list) or not league_leaders:
        return pl.DataFrame()
    rows: list[StatLeaderDict] = []
    for leader_group in league_leaders:
        if not isinstance(leader_group, dict):
            continue
        category = str(leader_group.get("leaderCategory", "unknown"))
        leaders = leader_group.get("leaders", [])
        if not isinstance(leaders, list):
            continue
        for entry in leaders:
            if isinstance(entry, dict):
                rows.append(parse_leader(cast(JsonObject, entry), category, season, stat_group))
    if not rows:
        return pl.DataFrame()
    return validate_and_cast_schema(
        pl.DataFrame(rows, schema=MLB_STAT_LEADERS_TYPES), MLB_STAT_LEADERS_REQUIRED, MLB_STAT_LEADERS_TYPES
    )


def parse_mlb_pitch_arsenal(data: JsonObject, person_id: int, season: int) -> pl.DataFrame:
    """Parse pitch arsenal data from MLB Stats API /people/{id}/stats response.

    Filters for splits where type.displayName is "pitchArsenal".
    Each split must contain core pitch fields or raises UpstreamParseError.

    Note:
        Raises UpstreamParseError if a pitch arsenal entry is missing
        code, description, percentage, or averageSpeed.
    """
    stats = data.get("stats", [])
    if not isinstance(stats, list):
        return pl.DataFrame()
    rows: list[PitchArsenalDict] = []
    for stat in stats:
        if not isinstance(stat, dict):
            continue
        type_dict = safe_child_dict(stat, "type")
        if type_dict.get("displayName") != _PITCH_ARSENAL_STATS_DISPLAY_NAME:
            continue
        splits = stat.get("splits", [])
        if not isinstance(splits, list):
            continue
        for split in splits:
            if isinstance(split, dict):
                rows.append(parse_pitch_arsenal(cast(JsonObject, split), person_id, season))
    if not rows:
        return pl.DataFrame()
    return validate_and_cast_schema(
        pl.DataFrame(rows, schema=MLB_PITCH_ARSENAL_TYPES), MLB_PITCH_ARSENAL_REQUIRED, MLB_PITCH_ARSENAL_TYPES
    )
