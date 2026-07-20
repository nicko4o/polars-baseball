import polars as pl

from polars_baseball._cache import cached
from polars_baseball._config import MLB_FIRST_YEAR
from polars_baseball._season import most_recent_season
from polars_baseball.apis.mlb._contracts import (
    MLB_ACTIVE_ROSTER_TYPE,
    MLB_CACHE_MAX_AGE,
    roster_cache_key,
    roster_url,
)
from polars_baseball.context import BaseballContext
from polars_baseball.exceptions import InvalidParameterError
from polars_baseball.gateways.mlb import MlbStatsGateway
from polars_baseball.parsers.mlb import parse_mlb_roster


@cached(key=roster_cache_key, max_age=MLB_CACHE_MAX_AGE)
async def _fetch_mlb_roster(
    team_id: int,
    season: int | None = None,
    roster_type: str = MLB_ACTIVE_ROSTER_TYPE,
    force_update: bool = False,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    url = roster_url(team_id)
    params: dict[str, object] = {"rosterType": roster_type}
    if season is not None:
        params["season"] = season
    ctx = context or BaseballContext.default()
    return await MlbStatsGateway(ctx).fetch(
        url, params, "Failed to fetch or parse MLB roster data", lambda d: parse_mlb_roster(d, team_id)
    )


async def mlb_roster(
    team_id: int,
    season: int | None = None,
    roster_type: str = MLB_ACTIVE_ROSTER_TYPE,
    force_update: bool = False,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch team roster from the MLB Stats API, filtered by roster_type.

    Typical roster_type values are "active" and "40Man". Returns an empty
    DataFrame when no roster data is available for the given team and season.

    Note:
        Raises InvalidParameterError if team_id is non-positive, the season
        is out of range, or roster_type is empty.
    """
    if team_id <= 0:
        raise InvalidParameterError("team_id must be a positive integer.")
    if season is not None and (season < MLB_FIRST_YEAR or season > most_recent_season() + 1):
        raise InvalidParameterError(f"Invalid season: {season}.")
    if not roster_type:
        raise InvalidParameterError("roster_type must be a non-empty string.")

    return await _fetch_mlb_roster(
        team_id=team_id,
        season=season,
        roster_type=roster_type,
        force_update=force_update,
        context=context,
    )
