"""MLB Stats API parser for roster data."""

from typing import cast

import polars as pl

from polars_baseball._json_utils import JsonObject, safe_child_dict
from polars_baseball._schema_utils import validate_and_cast_schema
from polars_baseball._schemas.mlb import MLB_ROSTER_REQUIRED, MLB_ROSTER_TYPES
from polars_baseball.parsers.mlb.types import RosterMemberDict


def parse_roster_member(roster_data: JsonObject, team_id: int) -> RosterMemberDict:
    person = safe_child_dict(roster_data, "person")
    pos = safe_child_dict(roster_data, "position")
    status = safe_child_dict(roster_data, "status")
    return cast(
        RosterMemberDict,
        {
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
        },
    )


def parse_mlb_roster(data: JsonObject, team_id: int) -> pl.DataFrame:
    """Parse roster from MLB Stats API /teams/{id}/roster response.

    Each roster member's person, position, and status sub-objects are
    flattened into a single row. Returns an empty DataFrame when the
    roster array is empty.
    """
    roster = data.get("roster", [])
    if not isinstance(roster, list) or not roster:
        return pl.DataFrame()
    rows = [parse_roster_member(cast(JsonObject, member), team_id) for member in roster if isinstance(member, dict)]
    if not rows:
        return pl.DataFrame()
    return validate_and_cast_schema(pl.DataFrame(rows, schema=MLB_ROSTER_TYPES), MLB_ROSTER_REQUIRED, MLB_ROSTER_TYPES)
