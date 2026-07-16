from typing import Any, cast

import polars as pl

from polars_baseball._schema_utils import validate_and_cast_schema
from polars_baseball._schemas.mlb import MLB_SCHEDULE_REQUIRED, MLB_SCHEDULE_TYPES
from polars_baseball.parsers.mlb.types import GameDict


def _team_info(game_data: dict[str, Any], team_type: str) -> tuple[Any, Any, Any, Any, Any]:
    teams = game_data.get("teams", {})
    team_side = teams.get(team_type, {}) if isinstance(teams, dict) else {}
    team = team_side.get("team", {}) if isinstance(team_side, dict) else {}
    probable_pitcher = team_side.get("probablePitcher", {}) if isinstance(team_side, dict) else {}
    return (
        team.get("id"),
        team.get("name"),
        team_side.get("score") if isinstance(team_side, dict) else None,
        probable_pitcher.get("id"),
        probable_pitcher.get("fullName"),
    )


def _line_score(game_data: dict[str, Any], team_type: str) -> tuple[Any, Any]:
    linescore = game_data.get("linescore", {})
    linescore_teams = linescore.get("teams", {}) if isinstance(linescore, dict) else {}
    team_line = linescore_teams.get(team_type, {}) if isinstance(linescore_teams, dict) else {}
    if not isinstance(team_line, dict):
        return None, None
    return team_line.get("hits"), team_line.get("errors")


def _decision_pitcher(game_data: dict[str, Any], decision_type: str) -> tuple[Any, Any]:
    decisions = game_data.get("decisions", {})
    decisions = decisions if isinstance(decisions, dict) else {}
    pitcher = decisions.get(decision_type, {})
    if not isinstance(pitcher, dict):
        return None, None
    return pitcher.get("id"), pitcher.get("fullName")


def _game_metadata(game_data: dict[str, Any]) -> dict[str, Any]:
    status = game_data.get("status", {})
    venue = game_data.get("venue", {})
    return {
        "gamePk": game_data.get("gamePk"),
        "gameType": game_data.get("gameType"),
        "season": game_data.get("season"),
        "gameDate": game_data.get("gameDate"),
        "officialDate": game_data.get("officialDate"),
        "statusAbstract": status.get("abstractGameState"),
        "statusCode": status.get("statusCode"),
        "statusDetailed": status.get("detailedState"),
        "venueId": venue.get("id"),
        "venueName": venue.get("name"),
        "doubleHeader": game_data.get("doubleHeader"),
        "gamedayType": game_data.get("gamedayType"),
        "tiebreaker": game_data.get("tiebreaker"),
        "calendarEventID": game_data.get("calendarEventID"),
        "seasonDisplay": game_data.get("seasonDisplay"),
        "dayNight": game_data.get("dayNight"),
        "description": game_data.get("description"),
        "scheduledInnings": game_data.get("scheduledInnings"),
        "gamesInSeries": game_data.get("gamesInSeries"),
        "seriesGameNumber": game_data.get("seriesGameNumber"),
        "seriesDescription": game_data.get("seriesDescription"),
    }


def parse_game(game_data: dict[str, Any]) -> GameDict:
    away_id, away_name, away_score, away_pitcher_id, away_pitcher_name = _team_info(game_data, "away")
    home_id, home_name, home_score, home_pitcher_id, home_pitcher_name = _team_info(game_data, "home")
    away_hits, away_errors = _line_score(game_data, "away")
    home_hits, home_errors = _line_score(game_data, "home")
    winner_id, winner_name = _decision_pitcher(game_data, "winner")
    loser_id, loser_name = _decision_pitcher(game_data, "loser")
    save_id, save_name = _decision_pitcher(game_data, "save")
    return cast(
        GameDict,
        {
            **_game_metadata(game_data),
            "awayTeamId": away_id,
            "awayTeamName": away_name,
            "awayScore": away_score,
            "awayProbablePitcherId": away_pitcher_id,
            "awayProbablePitcherName": away_pitcher_name,
            "homeTeamId": home_id,
            "homeTeamName": home_name,
            "homeScore": home_score,
            "homeProbablePitcherId": home_pitcher_id,
            "homeProbablePitcherName": home_pitcher_name,
            "awayHits": away_hits,
            "awayErrors": away_errors,
            "homeHits": home_hits,
            "homeErrors": home_errors,
            "winnerPitcherId": winner_id,
            "winnerPitcherName": winner_name,
            "loserPitcherId": loser_id,
            "loserPitcherName": loser_name,
            "savePitcherId": save_id,
            "savePitcherName": save_name,
        },
    )


def parse_mlb_schedule(data: dict[str, Any]) -> pl.DataFrame:
    dates = data.get("dates", [])
    if not dates:
        return pl.DataFrame()
    rows: list[GameDict] = []
    for schedule_date in dates:
        for game in schedule_date.get("games", []):
            rows.append(parse_game(game))
    if not rows:
        return pl.DataFrame()
    return validate_and_cast_schema(pl.DataFrame(rows), MLB_SCHEDULE_REQUIRED, MLB_SCHEDULE_TYPES)
