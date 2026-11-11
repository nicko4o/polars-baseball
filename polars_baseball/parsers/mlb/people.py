"""MLB Stats API parsers for people and awards data."""

from typing import cast

import polars as pl

from polars_baseball._json_utils import JsonObject, safe_child_dict
from polars_baseball._schema_utils import validate_and_cast_schema
from polars_baseball._schemas.mlb import (
    MLB_PEOPLE_AWARDS_REQUIRED,
    MLB_PEOPLE_AWARDS_TYPES,
    MLB_PEOPLE_REQUIRED,
    MLB_PEOPLE_TYPES,
)
from polars_baseball.parsers.mlb.types import PeopleAwardDict, PersonDict


def parse_person(person_data: JsonObject) -> PersonDict:
    pos = safe_child_dict(person_data, "primaryPosition")
    bat = safe_child_dict(person_data, "batSide")
    pitch = safe_child_dict(person_data, "pitchHand")
    return cast(
        PersonDict,
        {
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
        },
    )


def parse_people_award(award_data: JsonObject, person_id: int) -> PeopleAwardDict:
    team_data = safe_child_dict(award_data, "team")
    player_data = safe_child_dict(award_data, "player")
    position_data = safe_child_dict(player_data, "primaryPosition")
    return cast(
        PeopleAwardDict,
        {
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
        },
    )


def parse_mlb_people(data: JsonObject) -> pl.DataFrame:
    """Parse people from MLB Stats API /people response.

    Extracts biographical and positional fields from each entry in the
    people[] array. Nested objects (primaryPosition, batSide, pitchHand)
    are flattened into prefixed columns.
    """
    people = data.get("people", [])
    if not isinstance(people, list) or not people:
        return pl.DataFrame()
    rows = [parse_person(cast(JsonObject, person)) for person in people if isinstance(person, dict)]
    if not rows:
        return pl.DataFrame()
    return validate_and_cast_schema(pl.DataFrame(rows, schema=MLB_PEOPLE_TYPES), MLB_PEOPLE_REQUIRED, MLB_PEOPLE_TYPES)


def parse_mlb_people_awards(data: JsonObject, person_id: int) -> pl.DataFrame:
    """Parse awards from MLB Stats API /people/{id}/awards response.

    Each award entry is annotated with the person ID. Nested team and
    player position objects are flattened.

    Note:
        Non-dict entries in the awards array are silently skipped.
    """
    awards = data.get("awards", [])
    if not isinstance(awards, list) or not awards:
        return pl.DataFrame()
    rows = [parse_people_award(cast(JsonObject, award), person_id) for award in awards if isinstance(award, dict)]
    if not rows:
        return pl.DataFrame()
    return validate_and_cast_schema(
        pl.DataFrame(rows, schema=MLB_PEOPLE_AWARDS_TYPES), MLB_PEOPLE_AWARDS_REQUIRED, MLB_PEOPLE_AWARDS_TYPES
    )
