"""MLB Stats API parser for schedule data."""

from typing import Any, NamedTuple, cast

import polars as pl

from polars_baseball._schema_utils import validate_and_cast_schema
from polars_baseball._schemas.mlb import MLB_SCHEDULE_REQUIRED, MLB_SCHEDULE_TYPES
from polars_baseball.parsers.mlb.types import GameDict


class TeamInfo(NamedTuple):
    team_id: int | None
    team_name: str | None
    score: int | None
    probable_pitcher_id: int | None
    probable_pitcher_name: str | None


def _team_info(game_data: dict[str, Any], team_type: str) -> TeamInfo:
    teams = game_data.get("teams")
    if not isinstance(teams, dict):
        return TeamInfo(None, None, None, None, None)
    team_side = teams.get(team_type)
    if not isinstance(team_side, dict):
        return TeamInfo(None, None, None, None, None)
    team = team_side.get("team")
    team = team if isinstance(team, dict) else {}
    pitcher = team_side.get("probablePitcher")
    pitcher = pitcher if isinstance(pitcher, dict) else {}
    return TeamInfo(
        team_id=team.get("id"),
        team_name=team.get("name"),
        score=team_side.get("score"),
        probable_pitcher_id=pitcher.get("id"),
        probable_pitcher_name=pitcher.get("fullName"),
    )


class LineScore(NamedTuple):
    hits: int | None
    errors: int | None


class DecisionPitcher(NamedTuple):
    pitcher_id: int | None
    pitcher_name: str | None


def _line_score(game_data: dict[str, Any], team_type: str) -> LineScore:
    linescore = game_data.get("linescore")
    if not isinstance(linescore, dict):
        return LineScore(None, None)
    linescore_teams = linescore.get("teams")
    if not isinstance(linescore_teams, dict):
        return LineScore(None, None)
    team_line = linescore_teams.get(team_type)
    if not isinstance(team_line, dict):
        return LineScore(None, None)
    return LineScore(
        hits=team_line.get("hits"),
        errors=team_line.get("errors"),
    )


def _decision_pitcher(game_data: dict[str, Any], decision_type: str) -> DecisionPitcher:
    decisions = game_data.get("decisions")
    if not isinstance(decisions, dict):
        return DecisionPitcher(None, None)
    pitcher = decisions.get(decision_type)
    if not isinstance(pitcher, dict):
        return DecisionPitcher(None, None)
    return DecisionPitcher(
        pitcher_id=pitcher.get("id"),
        pitcher_name=pitcher.get("fullName"),
    )


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
    away = _team_info(game_data, "away")
    home = _team_info(game_data, "home")
    away_line = _line_score(game_data, "away")
    home_line = _line_score(game_data, "home")
    winner = _decision_pitcher(game_data, "winner")
    loser = _decision_pitcher(game_data, "loser")
    save = _decision_pitcher(game_data, "save")
    return cast(
        GameDict,
        {
            **_game_metadata(game_data),
            "awayTeamId": away.team_id,
            "awayTeamName": away.team_name,
            "awayScore": away.score,
            "awayProbablePitcherId": away.probable_pitcher_id,
            "awayProbablePitcherName": away.probable_pitcher_name,
            "homeTeamId": home.team_id,
            "homeTeamName": home.team_name,
            "homeScore": home.score,
            "homeProbablePitcherId": home.probable_pitcher_id,
            "homeProbablePitcherName": home.probable_pitcher_name,
            "awayHits": away_line.hits,
            "awayErrors": away_line.errors,
            "homeHits": home_line.hits,
            "homeErrors": home_line.errors,
            "winnerPitcherId": winner.pitcher_id,
            "winnerPitcherName": winner.pitcher_name,
            "loserPitcherId": loser.pitcher_id,
            "loserPitcherName": loser.pitcher_name,
            "savePitcherId": save.pitcher_id,
            "savePitcherName": save.pitcher_name,
        },
    )


def parse_mlb_schedule(data: dict[str, Any]) -> pl.DataFrame:
    """Parse schedule from MLB Stats API /schedule response.

    Iterates dates[].games[] across all dates in the response. Each
    game includes team info, scores, probable pitchers, decision
    pitchers, hits, errors, and venue/status metadata.
    """
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
