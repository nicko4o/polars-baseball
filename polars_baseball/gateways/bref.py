from __future__ import annotations

from collections.abc import Mapping
from datetime import timedelta
from typing import Literal

import polars as pl

from polars_baseball._cache import generate_cache_key
from polars_baseball._config import (
    BREF_GAME_LOGS_URL_TEMPLATE,
    BREF_ROOT,
    BREF_SPLITS_URL_TEMPLATE,
)
from polars_baseball._schema_utils import validate_and_cast_schema
from polars_baseball.client import BaseballClient
from polars_baseball.gateways.base import BaseGateway
from polars_baseball.parsers.bref import BRefGameLogParser, BRefSplitsParser, parse_bref_dataset


class BRefGateway(BaseGateway):
    """Gateway for querying and caching raw data from Baseball Reference."""

    def __init__(self, context: BaseballClient) -> None:
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

    async def get_bwar(
        self,
        stat_type: Literal["bat", "pitch"],
        required_cols: list[str],
        col_types: dict[str, pl.DataType | type[pl.DataType]],
        all_columns: bool = False,
    ) -> pl.DataFrame:
        url = f"{BREF_ROOT}/data/war_daily_{stat_type}.txt"
        df = await self.get_dataset(url, params={"return_all": all_columns})
        df = validate_and_cast_schema(df, required_cols, col_types)
        if not all_columns:
            existing = [c for c in col_types if c in df.columns]
            df = df.select(existing)
        return df

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
        split_type = "p" if pitching else "b"
        str_year = "Career" if year is None else str(year)
        url = BREF_SPLITS_URL_TEMPLATE.format(player_id=playerid, year=str_year, split_type=split_type)
        key = generate_cache_key("bref/splits_html", {"playerid": playerid, "year": str_year, "type": split_type})

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

    async def get_game_logs(
        self,
        player_id: str,
        year: int,
        log_type: str = "batting",
        *,
        headers: Mapping[str, str] | None = None,
        use_cache: bool = True,
        max_age: timedelta | None = None,
        force_update: bool = False,
    ) -> pl.DataFrame:
        """Fetch game log HTML from BRef and return parsed DataFrame."""
        bref_log_type = "b" if log_type == "batting" else "p"
        url = BREF_GAME_LOGS_URL_TEMPLATE.format(player_id=player_id, log_type=bref_log_type, year=year)
        parser = BRefGameLogParser(log_type)
        return await self._fetch_cached_df(
            url,
            None,
            parser=parser.parse,
            headers=headers,
            use_cache=use_cache,
            max_age=max_age,
            force_update=force_update,
            error_msg="Baseball Reference returned empty response.",
        )
