from typing import Any

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
