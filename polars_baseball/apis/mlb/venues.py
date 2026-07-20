import polars as pl

from polars_baseball._cache import cached
from polars_baseball.apis.mlb._contracts import (
    MLB_CACHE_MAX_AGE,
    venue_url,
    venues_cache_key,
    venues_url,
)
from polars_baseball.context import BaseballContext
from polars_baseball.exceptions import InvalidParameterError
from polars_baseball.gateways.mlb import MlbStatsGateway
from polars_baseball.parsers.mlb import parse_mlb_venues


@cached(key=venues_cache_key, max_age=MLB_CACHE_MAX_AGE)
async def _fetch_mlb_venues(
    venue_ids: int | list[int] | None = None,
    force_update: bool = False,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    params = {}
    if isinstance(venue_ids, int):
        url = venue_url(str(venue_ids))
    elif isinstance(venue_ids, list):
        url = venues_url()
        params["venueIds"] = ",".join(map(str, venue_ids))
    else:
        url = venues_url()

    ctx = context or BaseballContext.default()
    return await MlbStatsGateway(ctx).fetch(
        url,
        params,
        "Failed to fetch or parse MLB venues data",
        parse_mlb_venues,
    )


async def mlb_venues(
    venue_ids: int | list[int] | None = None,
    force_update: bool = False,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch MLB venue details.

    Args:
        venue_ids: Single venue ID or list of venue IDs.
        force_update: Bypass cache and fetch fresh data.
        context: Optional BaseballContext.
    """
    if isinstance(venue_ids, int):
        if venue_ids <= 0:
            raise InvalidParameterError("venue_ids must be a positive integer.")
    elif isinstance(venue_ids, list):
        for v in venue_ids:
            if not isinstance(v, int) or v <= 0:
                raise InvalidParameterError("All venue IDs in list must be positive integers.")

    return await _fetch_mlb_venues(
        venue_ids=venue_ids,
        force_update=force_update,
        context=context,
    )
