"""MLB Stats API parsers for people and awards data."""

from typing import Any

import polars as pl

from polars_baseball._schema_utils import validate_and_cast_schema
from polars_baseball._schemas.mlb import (
    MLB_PEOPLE_AWARDS_REQUIRED,
    MLB_PEOPLE_AWARDS_TYPES,
    MLB_PEOPLE_REQUIRED,
    MLB_PEOPLE_TYPES,
)
from polars_baseball.parsers.mlb.types import PeopleAwardDict, PersonDict


def parse_person(person_data: dict[str, Any]) -> PersonDict:
    pos = person_data.get("primaryPosition", {})
    bat = person_data.get("batSide", {})
    pitch = person_data.get("pitchHand", {})
    return {
        "id": person_data.get("id"),
        "fullName": person_data.get("fullName"),
        "firstName": person_data.get("firstName"),
        "lastName": person_data.get("lastName"),
        "primaryNumber": person_data.get("primaryNumber"),
        "birthDate": person_data.get("birthDate"),
        "currentAge": person_data.get("currentAge"),
        "birthCity": person_data.get("birthCity"),
        "birthStateProvince": person_data.get("birthStateProvince"),
        "birthCountry": person_data.get("birthCountry"),
        "height": person_data.get("height"),
        "weight": person_data.get("weight"),
        "active": person_data.get("active"),
        "primaryPositionCode": pos.get("code"),
        "primaryPositionName": pos.get("name"),
        "primaryPositionAbbrev": pos.get("abbreviation"),
        "useName": person_data.get("useName"),
        "boxscoreName": person_data.get("boxscoreName"),
        "gender": person_data.get("gender"),
        "isPlayer": person_data.get("isPlayer"),
        "isVerified": person_data.get("isVerified"),
        "draftYear": person_data.get("draftYear"),
        "mlbDebutDate": person_data.get("mlbDebutDate"),
        "batSideCode": bat.get("code"),
        "pitchHandCode": pitch.get("code"),
    }


def parse_people_award(award_data: dict[str, Any], person_id: int) -> PeopleAwardDict:
    team = award_data.get("team", {})
    player = award_data.get("player", {})
    team_data = team if isinstance(team, dict) else {}
    player_data = player if isinstance(player, dict) else {}
    position = player_data.get("primaryPosition", {})
    position_data = position if isinstance(position, dict) else {}
    return {
        "personId": person_id,
        "awardId": award_data.get("id"),
        "awardName": award_data.get("name"),
        "date": award_data.get("date"),
        "season": award_data.get("season"),
        "teamId": team_data.get("id"),
        "teamName": team_data.get("teamName"),
        "positionCode": position_data.get("code"),
        "positionName": position_data.get("name"),
        "positionType": position_data.get("type"),
        "positionAbbreviation": position_data.get("abbreviation"),
    }


def parse_mlb_people(data: dict[str, Any]) -> pl.DataFrame:
    """Parse people from MLB Stats API /people response.

    Extracts biographical and positional fields from each entry in the
    people[] array. Nested objects (primaryPosition, batSide, pitchHand)
    are flattened into prefixed columns.
    """
    people = data.get("people", [])
    if not people:
        return pl.DataFrame()
    rows = [parse_person(person) for person in people]
    return validate_and_cast_schema(pl.DataFrame(rows), MLB_PEOPLE_REQUIRED, MLB_PEOPLE_TYPES)


def parse_mlb_people_awards(data: dict[str, Any], person_id: int) -> pl.DataFrame:
    """Parse awards from MLB Stats API /people/{id}/awards response.

    Each award entry is annotated with the person ID. Nested team and
    player position objects are flattened.

    Note:
        Non-dict entries in the awards array are silently skipped.
    """
    awards = data.get("awards", [])
    if not awards:
        return pl.DataFrame()
    rows = [parse_people_award(award, person_id) for award in awards if isinstance(award, dict)]
    if not rows:
        return pl.DataFrame()
    return validate_and_cast_schema(pl.DataFrame(rows), MLB_PEOPLE_AWARDS_REQUIRED, MLB_PEOPLE_AWARDS_TYPES)
