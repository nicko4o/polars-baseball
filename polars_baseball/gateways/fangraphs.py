from collections.abc import Mapping

import polars as pl

from polars_baseball._cache import generate_cache_key
from polars_baseball.context import BaseballContext
from polars_baseball.parsers.fangraphs import FangraphsHTMLParser


class FanGraphsGateway:
    """Fetch, cache, and parse FanGraphs leaderboard responses."""

    def __init__(self, context: BaseballContext) -> None:
        self._context = context
        self._parser = FangraphsHTMLParser()

    async def get_leaderboard(self, url: str, params: Mapping[str, object]) -> pl.DataFrame:
        key = generate_cache_key(url, params)
        return await self._context.cache.get_or_fetch(
            key,
            lambda: self._fetch_and_parse(url, params),
        )

    async def _fetch_and_parse(self, url: str, params: Mapping[str, object]) -> pl.DataFrame:
        html = await self._context.http.get_text(url, params=params)
        return self._parser.parse(html)
