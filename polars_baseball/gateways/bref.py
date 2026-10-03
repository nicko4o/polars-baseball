from __future__ import annotations

from collections.abc import Mapping
from datetime import timedelta

import polars as pl

from polars_baseball._cache import generate_cache_key
from polars_baseball._config import BREF_ROOT
from polars_baseball.context import BaseballContext
from polars_baseball.gateways.base import BaseGateway
from polars_baseball.parsers.bref import BRefSplitsParser, parse_bref_dataset


class BRefGateway(BaseGateway):
    """Gateway for querying and caching raw data from Baseball Reference."""

    def __init__(self, context: BaseballContext) -> None:
        super().__init__(context)

    async def get_dataset(
        self,
        url: str,
        params: Mapping[str, object] | None = None,
        *,
        headers: Mapping[str, str] | None = None,
        use_cache: bool = True,
        max_age: timedelta | None = None,
        force_update: bool = False,
    ) -> pl.DataFrame:
        """Universal loader for BRef datasets.

        Parsing priority:
          1. Embedded CSV export table (<table id="csv_..."> or <div class="csv">).
          2. Standard display HTML DOM table via BRefHTMLParser.
          3. Plain raw CSV / text stream.
        """
        return await self._fetch_cached_df(
            url,
            params,
            parser=parse_bref_dataset,
            headers=headers,
            use_cache=use_cache,
            max_age=max_age,
            force_update=force_update,
            error_msg="Baseball Reference returned empty response.",
        )

    async def get_splits(
        self,
        playerid: str,
        year: int | None = None,
        pitching: bool = False,
        *,
        headers: Mapping[str, str] | None = None,
        use_cache: bool = True,
        max_age: timedelta | None = None,
        force_update: bool = False,
    ) -> tuple[pl.DataFrame, dict[str, str], pl.DataFrame]:
        """Fetch splits raw HTML and return parsed (df_main, player_info, df_level)."""
        pitch_or_bat = "p" if pitching else "b"
        str_year = "Career" if year is None else str(year)
        url = f"{BREF_ROOT}/players/split.fcgi?id={playerid}&year={str_year}&t={pitch_or_bat}"
        key = generate_cache_key("bref/splits_html", {"playerid": playerid, "year": str_year, "type": pitch_or_bat})

        html = await self._fetch_cached_raw(
            url,
            headers=headers,
            use_cache=use_cache,
            max_age=max_age,
            force_update=force_update,
            cache_key=key,
            error_msg="Baseball Reference returned empty response.",
        )
        return BRefSplitsParser(playerid, year, pitching).parse(html)
