from typing import Any

import polars as pl

from polars_baseball._schema_utils import validate_and_cast_schema
from polars_baseball._schemas.mlb import MLB_DRAFT_REQUIRED, MLB_DRAFT_TYPES
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


def parse_mlb_draft(data: dict[str, Any], year: int) -> pl.DataFrame:
    drafts = data.get("drafts", {})
    rounds = drafts.get("rounds", []) if isinstance(drafts, dict) else []
    rows: list[DraftPickDict] = []
    for draft_round in rounds:
        picks = draft_round.get("picks", [])
        for pick in picks:
            rows.append(parse_draft_pick(pick, year))
    if not rows:
        return pl.DataFrame()
    return validate_and_cast_schema(pl.DataFrame(rows), MLB_DRAFT_REQUIRED, MLB_DRAFT_TYPES)
