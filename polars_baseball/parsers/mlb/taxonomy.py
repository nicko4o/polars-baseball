from typing import Any

import polars as pl

from polars_baseball._schema_utils import validate_and_cast_schema
from polars_baseball._schemas.mlb import (
    MLB_DIVISIONS_REQUIRED,
    MLB_DIVISIONS_TYPES,
    MLB_LEAGUES_REQUIRED,
    MLB_LEAGUES_TYPES,
    MLB_TEAMS_REQUIRED,
    MLB_TEAMS_TYPES,
)
from polars_baseball.parsers.mlb.types import DivisionDict, LeagueDict, TeamDict


def parse_team(team_data: dict[str, Any], season: int | None) -> TeamDict:
    league = team_data.get("league", {})
    division = team_data.get("division", {})
    venue = team_data.get("venue", {})
    spring = team_data.get("springLeague", {})
    return {
        "id": team_data.get("id"),
        "name": team_data.get("name"),
        "abbreviation": team_data.get("abbreviation"),
        "teamName": team_data.get("teamName"),
        "locationName": team_data.get("locationName"),
        "leagueId": league.get("id"),
        "leagueName": league.get("name"),
        "divisionId": division.get("id"),
        "divisionName": division.get("name"),
        "venueId": venue.get("id"),
        "venueName": venue.get("name"),
        "springLeague": spring.get("name"),
        "season": season,
    }


def parse_division(division_data: dict[str, Any]) -> DivisionDict:
    league = division_data.get("league", {})
    sport = division_data.get("sport", {})
    league_data = league if isinstance(league, dict) else {}
    sport_data = sport if isinstance(sport, dict) else {}
    return {
        "id": division_data.get("id"),
        "name": division_data.get("name"),
        "nameShort": division_data.get("nameShort"),
        "abbreviation": division_data.get("abbreviation"),
        "season": division_data.get("season"),
        "leagueId": league_data.get("id"),
        "sportId": sport_data.get("id"),
        "hasWildcard": division_data.get("hasWildcard"),
        "sortOrder": division_data.get("sortOrder"),
        "numPlayoffTeams": division_data.get("numPlayoffTeams"),
        "active": division_data.get("active"),
    }


def parse_league(league_data: dict[str, Any]) -> LeagueDict:
    sport = league_data.get("sport", {})
    sport_data = sport if isinstance(sport, dict) else {}
    return {
        "id": league_data.get("id"),
        "name": league_data.get("name"),
        "nameShort": league_data.get("nameShort"),
        "abbreviation": league_data.get("abbreviation"),
        "orgCode": league_data.get("orgCode"),
        "season": league_data.get("season"),
        "seasonState": league_data.get("seasonState"),
        "active": league_data.get("active"),
        "sportId": sport_data.get("id"),
        "numTeams": league_data.get("numTeams"),
        "numGames": league_data.get("numGames"),
        "numWildcardTeams": league_data.get("numWildcardTeams"),
        "hasWildCard": league_data.get("hasWildCard"),
        "divisionsInUse": league_data.get("divisionsInUse"),
        "sortOrder": league_data.get("sortOrder"),
    }


def parse_mlb_teams(data: dict[str, Any], season: int | None) -> pl.DataFrame:
    teams = data.get("teams", [])
    if not teams:
        return pl.DataFrame()
    rows = [parse_team(team, season) for team in teams]
    return validate_and_cast_schema(pl.DataFrame(rows), MLB_TEAMS_REQUIRED, MLB_TEAMS_TYPES)


def parse_mlb_divisions(data: dict[str, Any]) -> pl.DataFrame:
    divisions = data.get("divisions", [])
    if not divisions:
        return pl.DataFrame()
    rows = [parse_division(division) for division in divisions if isinstance(division, dict)]
    if not rows:
        return pl.DataFrame()
    return validate_and_cast_schema(pl.DataFrame(rows), MLB_DIVISIONS_REQUIRED, MLB_DIVISIONS_TYPES)


def parse_mlb_leagues(data: dict[str, Any]) -> pl.DataFrame:
    leagues = data.get("leagues", [])
    if not leagues:
        return pl.DataFrame()
    rows = [parse_league(league) for league in leagues if isinstance(league, dict)]
    if not rows:
        return pl.DataFrame()
    return validate_and_cast_schema(pl.DataFrame(rows), MLB_LEAGUES_REQUIRED, MLB_LEAGUES_TYPES)
