from typing import Any

from polars_baseball.exceptions import UpstreamParseError
from polars_baseball.parsers.mlb.types import DraftPickDict


def parse_draft_pick(pick: dict[str, Any], year: int) -> DraftPickDict:
    person = pick.get("person", {})
    team = pick.get("team", {})
    school = pick.get("homeSchool", {})

    round_val = pick.get("pickRound") or pick.get("round")
    pick_number = pick.get("pickNumber")
    player_name = person.get("fullName")

    if round_val is None or pick_number is None or player_name is None:
        raise UpstreamParseError(
            f"Draft pick missing core fields: round={round_val}, pickNumber={pick_number}, playerName={player_name}"
        )

    return {
        "year": year,
        "round": str(round_val),
        "pickNumber": int(pick_number),
        "roundPickNumber": pick.get("roundPickNumber"),
        "playerName": player_name,
        "playerId": person.get("id"),
        "teamId": team.get("id"),
        "teamName": team.get("name"),
        "signingBonus": pick.get("signingBonus"),
        "homeSchool": school.get("name"),
    }
