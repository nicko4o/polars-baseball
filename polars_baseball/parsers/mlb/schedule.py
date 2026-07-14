from typing import Any

from polars_baseball.parsers.mlb.types import GameDict


def parse_game(game_data: dict[str, Any]) -> GameDict:
    status = game_data.get("status", {})
    teams = game_data.get("teams", {})
    away = teams.get("away", {})
    home = teams.get("home", {})
    venue = game_data.get("venue", {})
    away_probable_pitcher = away.get("probablePitcher", {})
    home_probable_pitcher = home.get("probablePitcher", {})

    linescore = game_data.get("linescore", {})
    linescore_teams = linescore.get("teams", {}) if isinstance(linescore, dict) else {}
    ls_away = linescore_teams.get("away", {}) if isinstance(linescore_teams, dict) else {}
    ls_home = linescore_teams.get("home", {}) if isinstance(linescore_teams, dict) else {}

    decisions = game_data.get("decisions", {})
    decisions = decisions if isinstance(decisions, dict) else {}
    winner = decisions.get("winner", {}) if isinstance(decisions, dict) else {}
    loser = decisions.get("loser", {}) if isinstance(decisions, dict) else {}
    save_pitcher = decisions.get("save", {}) if isinstance(decisions, dict) else {}

    return {
        "gamePk": game_data.get("gamePk"),
        "gameType": game_data.get("gameType"),
        "season": game_data.get("season"),
        "gameDate": game_data.get("gameDate"),
        "officialDate": game_data.get("officialDate"),
        "statusAbstract": status.get("abstractGameState"),
        "statusCode": status.get("statusCode"),
        "statusDetailed": status.get("detailedState"),
        "awayTeamId": away.get("team", {}).get("id"),
        "awayTeamName": away.get("team", {}).get("name"),
        "awayScore": away.get("score"),
        "awayProbablePitcherId": away_probable_pitcher.get("id"),
        "awayProbablePitcherName": away_probable_pitcher.get("fullName"),
        "homeTeamId": home.get("team", {}).get("id"),
        "homeTeamName": home.get("team", {}).get("name"),
        "homeScore": home.get("score"),
        "homeProbablePitcherId": home_probable_pitcher.get("id"),
        "homeProbablePitcherName": home_probable_pitcher.get("fullName"),
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
        "awayHits": ls_away.get("hits") if ls_away else None,
        "awayErrors": ls_away.get("errors") if ls_away else None,
        "homeHits": ls_home.get("hits") if ls_home else None,
        "homeErrors": ls_home.get("errors") if ls_home else None,
        "winnerPitcherId": winner.get("id") if winner else None,
        "winnerPitcherName": winner.get("fullName") if winner else None,
        "loserPitcherId": loser.get("id") if loser else None,
        "loserPitcherName": loser.get("fullName") if loser else None,
        "savePitcherId": save_pitcher.get("id") if save_pitcher else None,
        "savePitcherName": save_pitcher.get("fullName") if save_pitcher else None,
    }
