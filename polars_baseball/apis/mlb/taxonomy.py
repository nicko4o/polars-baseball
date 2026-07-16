import polars as pl

from polars_baseball._cache import cached
from polars_baseball._config import MLB_FIRST_YEAR
from polars_baseball._season import most_recent_season
from polars_baseball.apis.mlb._contracts import (
    MLB_CACHE_MAX_AGE,
    MLB_DEFAULT_SPORT_ID,
    divisions_cache_key,
    divisions_url,
    leagues_cache_key,
    leagues_url,
    teams_cache_key,
    teams_url,
)
from polars_baseball.context import BaseballContext, default_context
from polars_baseball.exceptions import InvalidParameterError
from polars_baseball.gateways.mlb import MlbStatsGateway
from polars_baseball.parsers.mlb import (
    parse_mlb_divisions,
    parse_mlb_leagues,
    parse_mlb_teams,
)


@cached(key=teams_cache_key, max_age=MLB_CACHE_MAX_AGE)
async def _fetch_mlb_teams(
    season: int | None = None,
    league_id: int | None = None,
    sport_id: int = MLB_DEFAULT_SPORT_ID,
    force_update: bool = False,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    url = teams_url()
    params: dict[str, object] = {"sportId": sport_id}
    if season is not None:
        params["season"] = season
    if league_id is not None:
        params["leagueId"] = league_id
    ctx = context or default_context()
    return await MlbStatsGateway(ctx).fetch(
        url, params, "Failed to fetch or parse MLB teams data", lambda d: parse_mlb_teams(d, season)
    )


@cached(key=divisions_cache_key, max_age=MLB_CACHE_MAX_AGE)
async def _fetch_mlb_divisions(
    sport_id: int = MLB_DEFAULT_SPORT_ID,
    force_update: bool = False,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    ctx = context or default_context()
    return await MlbStatsGateway(ctx).fetch(
        divisions_url(),
        {"sportId": sport_id},
        "Failed to fetch or parse MLB divisions data",
        parse_mlb_divisions,
    )


@cached(key=leagues_cache_key, max_age=MLB_CACHE_MAX_AGE)
async def _fetch_mlb_leagues(
    sport_id: int = MLB_DEFAULT_SPORT_ID,
    force_update: bool = False,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    ctx = context or default_context()
    return await MlbStatsGateway(ctx).fetch(
        leagues_url(),
        {"sportId": sport_id},
        "Failed to fetch or parse MLB leagues data",
        parse_mlb_leagues,
    )


async def mlb_teams(
    season: int | None = None,
    league_id: int | None = None,
    sport_id: int = MLB_DEFAULT_SPORT_ID,
    force_update: bool = False,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch MLB team information from the Stats API.

    If season is provided, returns only teams active for that season.
    Returns all teams across sports when no filters are applied.

    Edge Cases:
        Raises InvalidParameterError if season is provided but out of
        valid range, or if sport_id is non-positive.
    """
    if season is not None:
        if season <= 0:
            raise InvalidParameterError("season must be a positive integer.")
        if season < MLB_FIRST_YEAR or season > most_recent_season() + 1:
            raise InvalidParameterError(f"Invalid season: {season}.")
    if sport_id <= 0:
        raise InvalidParameterError("sport_id must be a positive integer.")

    return await _fetch_mlb_teams(
        season=season,
        league_id=league_id,
        sport_id=sport_id,
        force_update=force_update,
        context=context,
    )


async def mlb_divisions(
    sport_id: int = MLB_DEFAULT_SPORT_ID,
    force_update: bool = False,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch official MLB division dimension metadata from the Stats API."""
    if sport_id <= 0:
        raise InvalidParameterError("sport_id must be a positive integer.")

    return await _fetch_mlb_divisions(
        sport_id=sport_id,
        force_update=force_update,
        context=context,
    )


async def mlb_leagues(
    sport_id: int = MLB_DEFAULT_SPORT_ID,
    force_update: bool = False,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch official MLB league dimension metadata from the Stats API."""
    if sport_id <= 0:
        raise InvalidParameterError("sport_id must be a positive integer.")

    return await _fetch_mlb_leagues(
        sport_id=sport_id,
        force_update=force_update,
        context=context,
    )
