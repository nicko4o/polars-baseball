from typing import Any, cast

import polars as pl

from polars_baseball._schema_utils import validate_and_cast_schema
from polars_baseball._schemas.mlb import (
    MLB_BOXSCORE_REQUIRED,
    MLB_BOXSCORE_STATS_TYPES,
    MLB_BOXSCORE_TYPES,
    MLB_LINESCORE_REQUIRED,
    MLB_LINESCORE_TYPES,
    MLB_LIVE_FEED_REQUIRED,
    MLB_LIVE_FEED_TYPES,
    MLB_PBP_REQUIRED,
    MLB_PBP_TYPES,
)
from polars_baseball.parsers.mlb.types import BoxscorePlayerDict, LinescoreDict, LiveFeedPitchDict, PlayByPlayDict


def _parse_batting_order(player_data: dict[str, Any]) -> int | None:
    batting_order = player_data.get("battingOrder")
    if batting_order is None:
        return None
    try:
        return int(batting_order)
    except (TypeError, ValueError):
        return None


def parse_boxscore_player(
    player_data: dict[str, Any],
    game_pk: int,
    team_id: int,
) -> BoxscorePlayerDict:
    person = player_data.get("person", {})
    pos = player_data.get("position", {})
    stats = player_data.get("stats", {})
    batting_order = _parse_batting_order(player_data)
    row = {
        "gamePk": game_pk,
        "teamId": team_id,
        "personId": person.get("id"),
        "fullName": person.get("fullName"),
        "jerseyNumber": player_data.get("jerseyNumber"),
        "positionCode": pos.get("code"),
        "positionName": pos.get("name"),
        "positionAbbrev": pos.get("abbreviation"),
        "isInBattingOrder": batting_order is not None,
        "battingOrder": batting_order,
    }
    for group in ("batting", "pitching", "fielding"):
        group_stats = stats.get(group, {})
        for key, value in group_stats.items():
            if isinstance(value, dict):
                continue
            row[f"{group}_{key}"] = value
    return cast(BoxscorePlayerDict, row)


def parse_boxscore(data: dict[str, Any], game_pk: int) -> list[BoxscorePlayerDict]:
    rows: list[BoxscorePlayerDict] = []
    teams = data.get("teams", {})
    for team_type in ("away", "home"):
        team_data = teams.get(team_type, {})
        team_id = team_data.get("team", {}).get("id")
        players = team_data.get("players", {})
        for player_data in players.values():
            rows.append(parse_boxscore_player(player_data, game_pk, team_id))
    return rows


def parse_play(play: dict[str, Any], game_pk: int) -> PlayByPlayDict:
    about = play.get("about", {})
    result = play.get("result", {})
    matchup = play.get("matchup", {})
    count = play.get("count", {})
    batter = matchup.get("batter", {})
    pitcher = matchup.get("pitcher", {})
    return PlayByPlayDict(
        gamePk=game_pk,
        atBatIndex=about.get("atBatIndex"),
        inning=about.get("inning"),
        halfInning=about.get("halfInning"),
        batterId=batter.get("id"),
        batterName=batter.get("fullName"),
        pitcherId=pitcher.get("id"),
        pitcherName=pitcher.get("fullName"),
        description=result.get("description"),
        event=result.get("event"),
        eventType=result.get("eventType"),
        balls=count.get("balls"),
        strikes=count.get("strikes"),
        outs=count.get("outs"),
        homeScore=result.get("homeScore"),
        awayScore=result.get("awayScore"),
        rbi=result.get("rbi"),
        homeTeamWinProbability=play.get("homeTeamWinProbability"),
        awayTeamWinProbability=play.get("awayTeamWinProbability"),
        homeTeamWinProbabilityAdded=play.get("homeTeamWinProbabilityAdded"),
        leverageIndex=play.get("leverageIndex"),
        dramaIndex=play.get("dramaIndex"),
    )


def parse_live_feed_pitch(
    event_data: dict[str, Any],
    play_data: dict[str, Any],
    game_pk: int,
) -> LiveFeedPitchDict:
    about = play_data.get("about", {})
    matchup = play_data.get("matchup", {})
    batter = matchup.get("batter", {})
    pitcher = matchup.get("pitcher", {})
    details = event_data.get("details", {})
    pitch_type = details.get("type", {})
    pitch_data = event_data.get("pitchData", {})
    breaks = pitch_data.get("breaks", {})

    return {
        "gamePk": game_pk,
        "atBatIndex": about.get("atBatIndex"),
        "pitchIndex": event_data.get("index"),
        "pitchNumber": event_data.get("pitchNumber"),
        "playId": about.get("playId"),
        "batterId": batter.get("id"),
        "batterName": batter.get("fullName"),
        "pitcherId": pitcher.get("id"),
        "pitcherName": pitcher.get("fullName"),
        "event": details.get("event"),
        "description": details.get("description"),
        "pitchType": pitch_type.get("code"),
        "releaseSpeed": pitch_data.get("startSpeed"),
        "spinRate": breaks.get("spinRate"),
    }


def parse_linescore(data: dict[str, Any], game_pk: int) -> list[LinescoreDict]:
    innings = data.get("innings", [])
    if not isinstance(innings, list):
        return []
    rows: list[LinescoreDict] = []
    for inn in innings:
        if not isinstance(inn, dict):
            continue
        home = inn.get("home", {})
        away = inn.get("away", {})
        home_data = home if isinstance(home, dict) else {}
        away_data = away if isinstance(away, dict) else {}
        rows.append(
            {
                "gamePk": game_pk,
                "inning": inn.get("num"),
                "homeRuns": home_data.get("runs"),
                "homeHits": home_data.get("hits"),
                "homeErrors": home_data.get("errors"),
                "awayRuns": away_data.get("runs"),
                "awayHits": away_data.get("hits"),
                "awayErrors": away_data.get("errors"),
            }
        )
    return rows


def parse_mlb_boxscore(data: dict[str, Any], game_pk: int) -> pl.DataFrame:
    rows = parse_boxscore(data, game_pk)
    if not rows:
        return pl.DataFrame()
    return validate_and_cast_schema(pl.DataFrame(rows), MLB_BOXSCORE_REQUIRED, MLB_BOXSCORE_TYPES)


def parse_mlb_boxscore_stats(data: dict[str, Any], game_pk: int) -> pl.DataFrame:
    rows = parse_boxscore(data, game_pk)
    if not rows:
        return pl.DataFrame()
    return validate_and_cast_schema(pl.DataFrame(rows), MLB_BOXSCORE_REQUIRED, MLB_BOXSCORE_STATS_TYPES)


def parse_mlb_play_by_play(data: dict[str, Any], game_pk: int) -> pl.DataFrame:
    plays = data.get("allPlays", [])
    if not plays:
        return pl.DataFrame()
    rows = [parse_play(play, game_pk) for play in plays]
    return validate_and_cast_schema(pl.DataFrame(rows), MLB_PBP_REQUIRED, MLB_PBP_TYPES)


def parse_mlb_win_probability(data: object, game_pk: int) -> pl.DataFrame:
    if not isinstance(data, list):
        return pl.DataFrame()
    rows = [parse_play(play, game_pk) for play in data if isinstance(play, dict)]
    if not rows:
        return pl.DataFrame()
    return validate_and_cast_schema(pl.DataFrame(rows), MLB_PBP_REQUIRED, MLB_PBP_TYPES)


def parse_mlb_game_feed_live(data: dict[str, Any], game_pk: int) -> pl.DataFrame:
    live_data = data.get("liveData", {})
    plays = live_data.get("plays", {}) if isinstance(live_data, dict) else {}
    all_plays = plays.get("allPlays", []) if isinstance(plays, dict) else []
    rows: list[LiveFeedPitchDict] = []
    for play in all_plays:
        for event in play.get("playEvents", []):
            if event.get("isPitch"):
                rows.append(parse_live_feed_pitch(event, play, game_pk))
    if not rows:
        return pl.DataFrame()
    return validate_and_cast_schema(pl.DataFrame(rows), MLB_LIVE_FEED_REQUIRED, MLB_LIVE_FEED_TYPES)


def parse_mlb_game_linescore(data: dict[str, Any], game_pk: int) -> pl.DataFrame:
    rows = parse_linescore(data, game_pk)
    if not rows:
        return pl.DataFrame()
    return validate_and_cast_schema(pl.DataFrame(rows), MLB_LINESCORE_REQUIRED, MLB_LINESCORE_TYPES)
