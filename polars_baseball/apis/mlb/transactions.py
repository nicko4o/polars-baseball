import re

import polars as pl

from polars_baseball._cache import cached
from polars_baseball.apis.mlb._contracts import (
    MLB_CACHE_MAX_AGE,
    MLB_DEFAULT_SPORT_ID,
    transactions_cache_key,
    transactions_url,
)
from polars_baseball.context import BaseballContext, default_context
from polars_baseball.exceptions import InvalidParameterError
from polars_baseball.gateways.mlb import MlbStatsGateway
from polars_baseball.parsers.mlb import parse_mlb_transactions


@cached(key=transactions_cache_key, max_age=MLB_CACHE_MAX_AGE)
async def _fetch_mlb_transactions(
    date: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
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
    ctx = context or default_context()
    return await MlbStatsGateway(ctx).fetch(
        url,
        params,
        "Failed to fetch or parse MLB transactions data",
        parse_mlb_transactions,
    )


async def mlb_transactions(
    date: str | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    sport_id: int = MLB_DEFAULT_SPORT_ID,
    force_update: bool = False,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch MLB transaction details for specific date or date range.

    Args:
        date: Single date to fetch transactions (YYYY-MM-DD).
        start_date: Start of date range (YYYY-MM-DD).
        end_date: End of date range (YYYY-MM-DD).
        sport_id: Sport ID to filter transactions (default: 1 for MLB).
        force_update: Bypass cache and fetch fresh data.
        context: Optional BaseballContext.
    """
    if sport_id <= 0:
        raise InvalidParameterError("sport_id must be a positive integer.")

    for d_val, name in [(date, "date"), (start_date, "start_date"), (end_date, "end_date")]:
        if d_val is not None and not re.match(r"^\d{4}-\d{2}-\d{2}$", d_val):
            raise InvalidParameterError(f"Invalid format for parameter {name}. Must be YYYY-MM-DD.")

    return await _fetch_mlb_transactions(
        date=date,
        start_date=start_date,
        end_date=end_date,
        sport_id=sport_id,
        force_update=force_update,
        context=context,
    )
