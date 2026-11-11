from typing import NamedTuple, cast

import polars as pl

from polars_baseball._json_utils import JsonObject, safe_child_dict, to_int, to_str
from polars_baseball._schema_utils import validate_and_cast_schema
from polars_baseball._schemas.mlb import MLB_SCHEDULE_REQUIRED, MLB_SCHEDULE_TYPES
from polars_baseball.parsers.mlb.types import GameDict


class TeamInfo(NamedTuple):
    team_id: int | None
    team_name: str | None
    score: int | None
    probable_pitcher_id: int | None
    probable_pitcher_name: str | None


def _team_info(game_data: JsonObject, team_type: str) -> TeamInfo:
    teams = safe_child_dict(game_data, "teams")
    team_side = safe_child_dict(teams, team_type)
    team = safe_child_dict(team_side, "team")
    pitcher = safe_child_dict(team_side, "probablePitcher")
    return TeamInfo(
        team_id=to_int(team.get("id")),
        team_name=to_str(team.get("name")),
        score=to_int(team_side.get("score")),
        probable_pitcher_id=to_int(pitcher.get("id")),
        probable_pitcher_name=to_str(pitcher.get("fullName")),
    )


class LineScore(NamedTuple):
    hits: int | None
    errors: int | None


class DecisionPitcher(NamedTuple):
    pitcher_id: int | None
    pitcher_name: str | None


def _line_score(game_data: JsonObject, team_type: str) -> LineScore:
    linescore = safe_child_dict(game_data, "linescore")
    linescore_teams = safe_child_dict(linescore, "teams")
    team_line = safe_child_dict(linescore_teams, team_type)
    return LineScore(
        hits=to_int(team_line.get("hits")),
        errors=to_int(team_line.get("errors")),
    )


def _decision_pitcher(game_data: JsonObject, decision_type: str) -> DecisionPitcher:
    decisions = safe_child_dict(game_data, "decisions")
    pitcher = safe_child_dict(decisions, decision_type)
    return DecisionPitcher(
        pitcher_id=to_int(pitcher.get("id")),
        pitcher_name=to_str(pitcher.get("fullName")),
    )


def _game_metadata(game_data: JsonObject) -> JsonObject:
    status = safe_child_dict(game_data, "status")
    venue = safe_child_dict(game_data, "venue")
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


def parse_game(game_data: JsonObject) -> GameDict:
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


def parse_mlb_schedule(data: JsonObject) -> pl.DataFrame:
    """Parse schedule from MLB Stats API /schedule response.

    Iterates dates[].games[] across all dates in the response. Each
    game includes team info, scores, probable pitchers, decision
    pitchers, hits, errors, and venue/status metadata.
    """
    dates = data.get("dates", [])
    if not isinstance(dates, list) or not dates:
        return pl.DataFrame(schema=MLB_SCHEDULE_TYPES)

    rows: list[GameDict] = []
    for schedule_date in dates:
        if not isinstance(schedule_date, dict):
            continue
        games = schedule_date.get("games", [])
        if not isinstance(games, list):
            continue
        for game in games:
            if isinstance(game, dict):
                rows.append(parse_game(cast(JsonObject, game)))

    return validate_and_cast_schema(
        pl.DataFrame(rows, schema=MLB_SCHEDULE_TYPES), MLB_SCHEDULE_REQUIRED, MLB_SCHEDULE_TYPES
    )
