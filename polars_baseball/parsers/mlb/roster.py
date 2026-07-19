"""MLB Stats API parser for roster data."""

from typing import Any

import polars as pl

from polars_baseball._schema_utils import validate_and_cast_schema
from polars_baseball._schemas.mlb import MLB_ROSTER_REQUIRED, MLB_ROSTER_TYPES
from polars_baseball.parsers.mlb.types import RosterMemberDict


def parse_roster_member(roster_data: dict[str, Any], team_id: int) -> RosterMemberDict:
    person = roster_data.get("person", {})
    pos = roster_data.get("position", {})
    status = roster_data.get("status", {})
    return {
        "teamId": team_id,
        "personId": person.get("id"),
        "fullName": person.get("fullName"),
        "jerseyNumber": roster_data.get("jerseyNumber"),
        "positionCode": pos.get("code"),
        "positionName": pos.get("name"),
        "positionAbbrev": pos.get("abbreviation"),
        "positionType": pos.get("type"),
        "statusCode": status.get("code"),
        "statusDesc": status.get("description"),
    }


def parse_mlb_roster(data: dict[str, Any], team_id: int) -> pl.DataFrame:
    """Parse roster from MLB Stats API /teams/{id}/roster response.

    Each roster member's person, position, and status sub-objects are
    flattened into a single row. Returns an empty DataFrame when the
    roster array is empty.
    """
    roster = data.get("roster", [])
    if not roster:
        return pl.DataFrame()
    rows = [parse_roster_member(member, team_id) for member in roster]
    return validate_and_cast_schema(pl.DataFrame(rows), MLB_ROSTER_REQUIRED, MLB_ROSTER_TYPES)
