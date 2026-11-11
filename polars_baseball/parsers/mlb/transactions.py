"""MLB Stats API parser for transaction data."""

from typing import cast

import polars as pl

from polars_baseball._json_utils import JsonObject, safe_child_dict, to_int
from polars_baseball._schema_utils import validate_and_cast_schema
from polars_baseball._schemas.mlb import MLB_TRANSACTIONS_REQUIRED, MLB_TRANSACTIONS_TYPES
from polars_baseball.exceptions import UpstreamParseError
from polars_baseball.parsers.mlb.types import TransactionDict


def parse_transaction(tx: JsonObject) -> TransactionDict:
    tx_id_int = to_int(tx.get("id"))
    date = tx.get("date")
    description = tx.get("description")
    type_code = tx.get("typeCode")
    type_desc = tx.get("typeDesc")

    if tx_id_int is None or date is None or description is None or type_code is None or type_desc is None:
        raise UpstreamParseError(
            f"Transaction missing core fields: id={tx.get('id')}, date={date}, description={description}, "
            f"typeCode={type_code}, typeDesc={type_desc}"
        )

    person = safe_child_dict(tx, "person")
    from_team = safe_child_dict(tx, "fromTeam")
    to_team = safe_child_dict(tx, "toTeam")

    effective_date = tx.get("effectiveDate")
    resolution_date = tx.get("resolutionDate")

    return cast(
        TransactionDict,
        {
            "id": tx_id_int,
            "date": str(date),
            "effectiveDate": str(effective_date) if effective_date is not None else None,
            "resolutionDate": str(resolution_date) if resolution_date is not None else None,
            "description": str(description),
            "typeCode": str(type_code),
            "typeDesc": str(type_desc),
            "playerId": person.get("id"),
            "playerName": person.get("fullName"),
            "fromTeamId": from_team.get("id"),
            "fromTeamName": from_team.get("name"),
            "toTeamId": to_team.get("id"),
            "toTeamName": to_team.get("name"),
        },
    )


def parse_mlb_transactions(data: JsonObject) -> pl.DataFrame:
    """Parse transactions from MLB Stats API /transactions response.

    Each transaction must have core fields (id, date, description,
    typeCode, typeDesc) or raises UpstreamParseError. Person, fromTeam,
    and toTeam sub-objects are flattened into the row.

    Note:
        Raises UpstreamParseError when a transaction is missing any
        required core field.
    """
    transactions = data.get("transactions", [])
    if not isinstance(transactions, list) or not transactions:
        return pl.DataFrame()
    rows = [parse_transaction(cast(JsonObject, tx)) for tx in transactions if isinstance(tx, dict)]
    if not rows:
        return pl.DataFrame()
    return validate_and_cast_schema(
        pl.DataFrame(rows, schema=MLB_TRANSACTIONS_TYPES), MLB_TRANSACTIONS_REQUIRED, MLB_TRANSACTIONS_TYPES
    )
