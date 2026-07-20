import polars as pl

from polars_baseball._cache import cached
from polars_baseball._config import MLB_FIRST_YEAR
from polars_baseball._season import most_recent_season
from polars_baseball.apis.mlb._contracts import MLB_CACHE_MAX_AGE, draft_cache_key, draft_url
from polars_baseball.context import BaseballContext
from polars_baseball.exceptions import InvalidParameterError
from polars_baseball.gateways.mlb import MlbStatsGateway
from polars_baseball.parsers.mlb import parse_mlb_draft


@cached(key=draft_cache_key, max_age=MLB_CACHE_MAX_AGE)
async def _fetch_mlb_draft(
    year: int,
    force_update: bool = False,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    url = draft_url(year)
    ctx = context or BaseballContext.default()
    return await MlbStatsGateway(ctx).fetch(
        url,
        None,
        "Failed to fetch or parse MLB draft data",
        lambda d: parse_mlb_draft(d, year),
    )


async def mlb_draft(
    year: int,
    draft_round: int | None = None,
    team_id: int | None = None,
    force_update: bool = False,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch MLB draft details for a specific season from the MLB Stats API.

    Args:
        year: The draft season (e.g. 2025).
        draft_round: Optional round filter (e.g. 1).
        team_id: Optional team ID filter (e.g. 119).
        force_update: Bypass cache and fetch fresh data.
        context: Optional BaseballContext.
    """
    if year < MLB_FIRST_YEAR or year > most_recent_season() + 1:
        raise InvalidParameterError(f"Invalid draft season: {year}.")
    if draft_round is not None and draft_round <= 0:
        raise InvalidParameterError("draft_round must be a positive integer.")
    if team_id is not None and team_id <= 0:
        raise InvalidParameterError("team_id must be a positive integer.")

    df = await _fetch_mlb_draft(year=year, force_update=force_update, context=context)
    if df.is_empty():
        return df

    if draft_round is not None:
        df = df.filter(pl.col("round").cast(pl.Int64, strict=False) == draft_round)
    if team_id is not None:
        df = df.filter(pl.col("teamId") == team_id)
    return df
