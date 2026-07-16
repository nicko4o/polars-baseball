import json

import polars as pl

from polars_baseball._cache import CacheCallArgs, cached, generate_cache_key
from polars_baseball._config import MLB_FIRST_YEAR, STATS_API_ROOT
from polars_baseball._season import most_recent_season
from polars_baseball.context import BaseballContext, default_context
from polars_baseball.exceptions import InvalidParameterError, UpstreamParseError
from polars_baseball.parsers.standings import parse_standings_payload

_PRE_DEAD_BALL_START = MLB_FIRST_YEAR


def _standings_cache_key(call: CacheCallArgs) -> str:
    season = call.argument("season", int)
    url = f"{STATS_API_ROOT}/standings?leagueId=103,104&season={season}"
    return generate_cache_key(url, {})


@cached(key=_standings_cache_key)
async def _fetch_standings(season: int, context: BaseballContext | None = None) -> pl.DataFrame:
    ctx = context or default_context()
    url = f"{STATS_API_ROOT}/standings?leagueId=103,104&season={season}"
    try:
        res = ctx.http.get_text(url)
        html = await res if not isinstance(res, str) else res
        data = json.loads(html)
    except Exception as e:
        raise UpstreamParseError(f"Failed to fetch or parse standings from MLB Stats API: {e}") from e

    return parse_standings_payload(data, season)


async def standings(season: int | None = None, context: BaseballContext | None = None) -> pl.DataFrame:
    """Fetch division standings from the MLB Stats API for a given season.

    Returns one DataFrame with division metadata and team-level standings.

    Edge Cases:
        - Raises ``InvalidParameterError`` for seasons before 1901 (``MLB_FIRST_YEAR``).
        - Defaults to the most recent completed season when ``season`` is omitted.
        - Games Back (``GB``) is ``None`` for division leaders or tied values.
    """
    if season is None:
        season = most_recent_season()
    if season < _PRE_DEAD_BALL_START:
        raise InvalidParameterError(
            f"This query currently only returns standings until the {_PRE_DEAD_BALL_START} season. "
            f"Try looking at years from {_PRE_DEAD_BALL_START} to present."
        )
    return await _fetch_standings(season, context=context)
