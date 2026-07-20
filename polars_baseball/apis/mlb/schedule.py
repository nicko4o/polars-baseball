import re

import polars as pl

from polars_baseball._cache import cached
from polars_baseball._config import MLB_FIRST_YEAR
from polars_baseball._season import most_recent_season
from polars_baseball.apis.mlb._contracts import (
    MLB_CACHE_MAX_AGE,
    MLB_DEFAULT_SPORT_ID,
    MLB_POSTSEASON_GAME_TYPE,
    postseason_cache_key,
    schedule_cache_key,
    schedule_url,
)
from polars_baseball.context import BaseballContext
from polars_baseball.exceptions import InvalidParameterError
from polars_baseball.gateways.mlb import MlbStatsGateway
from polars_baseball.parsers.mlb import parse_mlb_schedule


@cached(key=schedule_cache_key, max_age=MLB_CACHE_MAX_AGE)
async def _fetch_mlb_schedule(
    season: int | None = None,
    date: str | None = None,
    team_id: int | None = None,
    hydrate: str | None = None,
    force_update: bool = False,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    params: dict[str, object] = {"sportId": MLB_DEFAULT_SPORT_ID}
    if season is not None:
        params["season"] = season
    if date is not None:
        params["date"] = date
    if team_id is not None:
        params["teamId"] = team_id
    if hydrate is not None:
        params["hydrate"] = hydrate
    ctx = context or BaseballContext.default()
    return await MlbStatsGateway(ctx).fetch(
        schedule_url(), params, "Failed to fetch or parse MLB schedule data", parse_mlb_schedule
    )


@cached(key=postseason_cache_key, max_age=MLB_CACHE_MAX_AGE)
async def _fetch_mlb_postseason_schedule(
    season: int,
    force_update: bool = False,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    params: dict[str, object] = {
        "gameType": MLB_POSTSEASON_GAME_TYPE,
        "sportId": MLB_DEFAULT_SPORT_ID,
        "season": season,
    }
    ctx = context or BaseballContext.default()
    return await MlbStatsGateway(ctx).fetch(
        schedule_url(), params, "Failed to fetch or parse MLB postseason schedule", parse_mlb_schedule
    )


async def mlb_schedule(
    season: int | None = None,
    date: str | None = None,
    team_id: int | None = None,
    hydrate: str | None = None,
    force_update: bool = False,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch MLB schedule for a season, date, and/or team from the Stats API.

    At least one of season or date must be provided. season is validated
    against the valid MLB season range.

    Note:
        Raises InvalidParameterError if neither season nor date is given,
        the season is out of range, date is not in YYYY-MM-DD format, or
        team_id is non-positive.
    """
    if season is None and date is None:
        raise InvalidParameterError("Either season or date must be provided.")
    if season is not None and (season < MLB_FIRST_YEAR or season > most_recent_season() + 1):
        raise InvalidParameterError(f"Invalid season: {season}.")
    if team_id is not None and team_id <= 0:
        raise InvalidParameterError("team_id must be a positive integer.")
    if date is not None and not re.match(r"^\d{4}-\d{2}-\d{2}$", date):
        raise InvalidParameterError("date must be in YYYY-MM-DD format.")
    if hydrate is not None and not hydrate:
        raise InvalidParameterError("hydrate must be a non-empty string.")

    return await _fetch_mlb_schedule(
        season=season,
        date=date,
        team_id=team_id,
        hydrate=hydrate,
        force_update=force_update,
        context=context,
    )


async def mlb_postseason_schedule(
    season: int,
    force_update: bool = False,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch postseason schedule for a season from the MLB Stats API.

    Returns only playoff games (gameType "P") for the specified season.
    Returns an empty DataFrame when no postseason data is available.

    Note:
        Raises InvalidParameterError if the season is out of valid range.
    """
    if season < MLB_FIRST_YEAR or season > most_recent_season() + 1:
        raise InvalidParameterError(f"Invalid season: {season}.")

    return await _fetch_mlb_postseason_schedule(
        season=season,
        force_update=force_update,
        context=context,
    )
