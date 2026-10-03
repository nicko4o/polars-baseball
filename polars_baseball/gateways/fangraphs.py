from __future__ import annotations

from collections.abc import Mapping
from datetime import timedelta

import polars as pl

from polars_baseball.context import BaseballContext
from polars_baseball.gateways.base import BaseGateway
from polars_baseball.parsers.fangraphs import FangraphsHTMLParser


class FanGraphsGateway(BaseGateway):
    """Fetch, cache, and parse FanGraphs leaderboard responses."""

    def __init__(self, context: BaseballContext, *, parser: FangraphsHTMLParser | None = None) -> None:
        super().__init__(context)
        self._parser = parser or FangraphsHTMLParser()

    async def get_leaderboard(
        self,
        url: str,
        params: Mapping[str, object],
        *,
        use_cache: bool = True,
        max_age: timedelta | None = None,
        force_update: bool = False,
        parser: FangraphsHTMLParser | None = None,
    ) -> pl.DataFrame:
        active_parser = parser or self._parser
        return await self._fetch_cached_df(
            url,
            params,
            parser=active_parser.parse,
            use_cache=use_cache,
            max_age=max_age,
            force_update=force_update,
            error_msg="FanGraphs returned empty response.",
        )
