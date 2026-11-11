"""MLB Stats API parsers for team, division, and league taxonomy data."""

from typing import cast

import polars as pl

from polars_baseball._json_utils import JsonObject, safe_child_dict
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


def parse_team(team_data: JsonObject, season: int | None) -> TeamDict:
    league = safe_child_dict(team_data, "league")
    division = safe_child_dict(team_data, "division")
    venue = safe_child_dict(team_data, "venue")
    spring = safe_child_dict(team_data, "springLeague")
    return cast(
        TeamDict,
        {
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
        },
    )


def parse_division(division_data: JsonObject) -> DivisionDict:
    league = safe_child_dict(division_data, "league")
    sport = safe_child_dict(division_data, "sport")
    return cast(
        DivisionDict,
        {
            "id": division_data.get("id"),
            "name": division_data.get("name"),
            "nameShort": division_data.get("nameShort"),
            "abbreviation": division_data.get("abbreviation"),
            "season": division_data.get("season"),
            "leagueId": league.get("id"),
            "sportId": sport.get("id"),
            "hasWildcard": division_data.get("hasWildcard"),
            "sortOrder": division_data.get("sortOrder"),
            "numPlayoffTeams": division_data.get("numPlayoffTeams"),
            "active": division_data.get("active"),
        },
    )


def parse_league(league_data: JsonObject) -> LeagueDict:
    sport = safe_child_dict(league_data, "sport")
    return cast(
        LeagueDict,
        {
            "id": league_data.get("id"),
            "name": league_data.get("name"),
            "nameShort": league_data.get("nameShort"),
            "abbreviation": league_data.get("abbreviation"),
            "orgCode": league_data.get("orgCode"),
            "season": league_data.get("season"),
            "seasonState": league_data.get("seasonState"),
            "active": league_data.get("active"),
            "sportId": sport.get("id"),
            "numTeams": league_data.get("numTeams"),
            "numGames": league_data.get("numGames"),
            "numWildcardTeams": league_data.get("numWildcardTeams"),
            "hasWildCard": league_data.get("hasWildCard"),
            "divisionsInUse": league_data.get("divisionsInUse"),
            "sortOrder": league_data.get("sortOrder"),
        },
    )


def parse_mlb_teams(data: JsonObject, season: int | None) -> pl.DataFrame:
    """Parse teams from MLB Stats API /teams response.

    Each team entry flattens league, division, venue, and springLeague
    sub-objects. Annotated with the requested season parameter.
    """
    teams = data.get("teams", [])
    if not isinstance(teams, list) or not teams:
        return pl.DataFrame()
    rows = [parse_team(cast(JsonObject, team), season) for team in teams if isinstance(team, dict)]
    if not rows:
        return pl.DataFrame()
    return validate_and_cast_schema(pl.DataFrame(rows, schema=MLB_TEAMS_TYPES), MLB_TEAMS_REQUIRED, MLB_TEAMS_TYPES)


def parse_mlb_divisions(data: JsonObject) -> pl.DataFrame:
    """Parse divisions from MLB Stats API /divisions response.

    Each division entry flattens league and sport sub-objects.

    Note:
        Non-dict entries in the divisions array are silently skipped.
    """
    divisions = data.get("divisions", [])
    if not isinstance(divisions, list) or not divisions:
        return pl.DataFrame()
    rows = [parse_division(cast(JsonObject, division)) for division in divisions if isinstance(division, dict)]
    if not rows:
        return pl.DataFrame()
    return validate_and_cast_schema(
        pl.DataFrame(rows, schema=MLB_DIVISIONS_TYPES), MLB_DIVISIONS_REQUIRED, MLB_DIVISIONS_TYPES
    )


def parse_mlb_leagues(data: JsonObject) -> pl.DataFrame:
    """Parse leagues from MLB Stats API /leagues response.

    Each league entry flattens the sport sub-object.

    Note:
        Non-dict entries in the leagues array are silently skipped.
    """
    leagues = data.get("leagues", [])
    if not isinstance(leagues, list) or not leagues:
        return pl.DataFrame()
    rows = [parse_league(cast(JsonObject, league)) for league in leagues if isinstance(league, dict)]
    if not rows:
        return pl.DataFrame()
    return validate_and_cast_schema(
        pl.DataFrame(rows, schema=MLB_LEAGUES_TYPES), MLB_LEAGUES_REQUIRED, MLB_LEAGUES_TYPES
    )
