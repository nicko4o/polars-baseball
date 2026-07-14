from typing import Any

from polars_baseball.exceptions import UpstreamParseError
from polars_baseball.parsers.mlb.types import TransactionDict


def parse_transaction(tx: dict[str, Any]) -> TransactionDict:
    tx_id = tx.get("id")
    date = tx.get("date")
    description = tx.get("description")
    type_code = tx.get("typeCode")
    type_desc = tx.get("typeDesc")

    if tx_id is None or date is None or description is None or type_code is None or type_desc is None:
        raise UpstreamParseError(
            f"Transaction missing core fields: id={tx_id}, date={date}, description={description}, "
            f"typeCode={type_code}, typeDesc={type_desc}"
        )

    person = tx.get("person", {})
    from_team = tx.get("fromTeam", {})
    to_team = tx.get("toTeam", {})

    return {
        "id": int(tx_id),
        "date": str(date),
        "description": str(description),
        "typeCode": str(type_code),
        "typeDesc": str(type_desc),
        "playerId": person.get("id"),
        "playerName": person.get("fullName"),
        "fromTeamId": from_team.get("id"),
        "fromTeamName": from_team.get("name"),
        "toTeamId": to_team.get("id"),
        "toTeamName": to_team.get("name"),
    }
