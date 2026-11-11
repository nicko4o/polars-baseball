"""MLB Stats API parser for draft data."""

from typing import cast

import polars as pl

from polars_baseball._json_utils import JsonObject, safe_child_dict, to_int
from polars_baseball._schema_utils import validate_and_cast_schema
from polars_baseball._schemas.mlb import MLB_DRAFT_REQUIRED, MLB_DRAFT_TYPES
from polars_baseball.exceptions import UpstreamParseError
from polars_baseball.parsers.mlb.types import DraftPickDict


def parse_draft_pick(pick: JsonObject, year: int) -> DraftPickDict:
    person = safe_child_dict(pick, "person")
    team = safe_child_dict(pick, "team")
    school = safe_child_dict(pick, "homeSchool")

    round_val = pick.get("pickRound") or pick.get("round")
    pick_num = to_int(pick.get("pickNumber"))
    player_name = person.get("fullName")

    if round_val is None or pick_num is None or player_name is None:
        raise UpstreamParseError(
            f"Draft pick missing core fields: round={round_val}, pickNumber={pick.get('pickNumber')}, playerName={player_name}"
        )

    return cast(
        DraftPickDict,
        {
            "year": year,
            "round": str(round_val),
            "pickNumber": pick_num,
            "roundPickNumber": pick.get("roundPickNumber"),
            "playerName": player_name,
            "playerId": person.get("id"),
            "teamId": team.get("id"),
            "teamName": team.get("name"),
            "signingBonus": pick.get("signingBonus"),
            "homeSchool": school.get("name"),
        },
    )


def parse_mlb_draft(data: JsonObject, year: int) -> pl.DataFrame:
    """Parse draft picks from MLB Stats API /draft response.

    Navigates drafts.rounds[].picks[] to extract each draft pick. Each
    pick must have round, pickNumber, and playerName or raises
    UpstreamParseError.

    Note:
        Raises UpstreamParseError when a draft pick is missing any
        required core field.
    """
    drafts = safe_child_dict(data, "drafts")
    rounds = drafts.get("rounds", [])
    if not isinstance(rounds, list) or not rounds:
        return pl.DataFrame()

    rows: list[DraftPickDict] = []
    for draft_round in rounds:
        if not isinstance(draft_round, dict):
            continue
        picks = draft_round.get("picks", [])
        if not isinstance(picks, list):
            continue
        for pick in picks:
            if isinstance(pick, dict):
                rows.append(parse_draft_pick(cast(JsonObject, pick), year))

    if not rows:
        return pl.DataFrame()
    return validate_and_cast_schema(pl.DataFrame(rows, schema=MLB_DRAFT_TYPES), MLB_DRAFT_REQUIRED, MLB_DRAFT_TYPES)
