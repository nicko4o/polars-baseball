import re
from datetime import date as date_type

import polars as pl

from polars_baseball._cache import cached
from polars_baseball._season import coerce_datestring
from polars_baseball.apis.mlb._contracts import (
    MLB_CACHE_MAX_AGE,
    MLB_DEFAULT_SPORT_ID,
    transactions_cache_key,
    transactions_url,
)
from polars_baseball.context import BaseballContext
from polars_baseball.exceptions import InvalidParameterError
from polars_baseball.gateways.mlb import MlbStatsGateway
from polars_baseball.parsers.mlb import parse_mlb_transactions


@cached(key=transactions_cache_key, max_age=MLB_CACHE_MAX_AGE)
async def _fetch_mlb_transactions(
    date: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    team_id: int | None = None,
    player_id: int | None = None,
    sport_id: int = MLB_DEFAULT_SPORT_ID,
    force_update: bool = False,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    url = transactions_url()
    params: dict[str, object] = {"sportId": sport_id}
    if date:
        params["date"] = date
    if start_date:
        params["startDate"] = start_date
    if end_date:
        params["endDate"] = end_date
    if team_id is not None:
        params["teamId"] = team_id
    if player_id is not None:
        params["playerId"] = player_id
    ctx = context or BaseballContext.default()
    return await MlbStatsGateway(ctx).fetch(
        url,
        params,
        "Failed to fetch or parse MLB transactions data",
        parse_mlb_transactions,
    )


def _validate_transactions_params(
    date: str | None,
    start_date: str | None,
    end_date: str | None,
    team_id: int | None,
    player_id: int | None,
    sport_id: int,
) -> None:
    if date is None and start_date is None and end_date is None and team_id is None and player_id is None:
        raise InvalidParameterError(
            "Must specify at least one filter: date, start_date/end_date, team_id, or player_id."
        )
    if date is not None and (start_date is not None or end_date is not None):
        raise InvalidParameterError("Provide either date or start_date/end_date, not both.")
    if sport_id <= 0:
        raise InvalidParameterError("sport_id must be a positive integer.")
    if team_id is not None and team_id <= 0:
        raise InvalidParameterError("team_id must be a positive integer.")
    if player_id is not None and player_id <= 0:
        raise InvalidParameterError("player_id must be a positive integer.")

    for d_val, name in [(date, "date"), (start_date, "start_date"), (end_date, "end_date")]:
        if d_val is not None and not re.match(r"^\d{4}-\d{2}-\d{2}$", d_val):
            raise InvalidParameterError(f"Invalid format for parameter {name}. Must be YYYY-MM-DD.")


async def mlb_transactions(
    date: date_type | str | None = None,
    start_date: date_type | str | None = None,
    end_date: date_type | str | None = None,
    team_id: int | None = None,
    player_id: int | None = None,
    sport_id: int = MLB_DEFAULT_SPORT_ID,
    force_update: bool = False,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch MLB transaction details for specific date, date range, team, or player.

    Args:
        date: Single date to fetch transactions (YYYY-MM-DD or datetime.date).
        start_date: Start of date range (YYYY-MM-DD or datetime.date).
        end_date: End of date range (YYYY-MM-DD or datetime.date).
        team_id: Filter transactions by specific team ID.
        player_id: Filter transactions by specific player ID.
        sport_id: Sport ID to filter transactions (default: 1 for MLB).
        force_update: Bypass cache and fetch fresh data.
        context: Optional BaseballContext.
    """
    coerced_date = coerce_datestring(date)
    coerced_start_date = coerce_datestring(start_date)
    coerced_end_date = coerce_datestring(end_date)

    _validate_transactions_params(
        date=coerced_date,
        start_date=coerced_start_date,
        end_date=coerced_end_date,
        team_id=team_id,
        player_id=player_id,
        sport_id=sport_id,
    )

    return await _fetch_mlb_transactions(
        date=coerced_date,
        start_date=coerced_start_date,
        end_date=coerced_end_date,
        team_id=team_id,
        player_id=player_id,
        sport_id=sport_id,
        force_update=force_update,
        context=context,
    )
