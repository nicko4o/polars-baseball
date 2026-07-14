import io
from collections.abc import Mapping
from datetime import timedelta

import polars as pl

from polars_baseball._cache import generate_cache_key
from polars_baseball._config import BREF_ROOT
from polars_baseball.context import BaseballContext
from polars_baseball.parsers._strategy import ProviderChain
from polars_baseball.parsers.base import BaseParser
from polars_baseball.parsers.bref import BRefHTMLParser, BRefSplitsParser
from polars_baseball.parsers.bref_standard_strategy import BRefCSVExportStrategy, BRefStandardStrategy


def _build_default_chain(parser: BaseParser) -> ProviderChain | None:
    if isinstance(parser, BRefHTMLParser):
        return ProviderChain([BRefCSVExportStrategy(), BRefStandardStrategy(parser)])
    return None


class BRefGateway:
    """Gateway for querying and caching raw data from Baseball Reference."""

    def __init__(self, context: BaseballContext) -> None:
        self._context = context

    async def get_dataset(
        self,
        url: str,
        params: Mapping[str, object] | None = None,
        parser: BaseParser | None = None,
        *,
        headers: Mapping[str, str] | None = None,
        use_cache: bool = True,
        max_age: timedelta | None = None,
        force_update: bool = False,
        chain: ProviderChain | None = None,
    ) -> pl.DataFrame:
        """Universal loader for BRef datasets.

        Parsing priority:
          1. chain: ProviderChain with multiple strategies (try each in order).
          2. parser: Single legacy parser (automatically wrapped with CSV fallback).
          3. Neither: Fallback to pl.read_csv (for raw CSV endpoints).
        """
        key = generate_cache_key(url, params)
        if not use_cache:
            raw_text = await self._context.http.get_text(url, params=params, headers=headers)
            if not raw_text:
                return pl.DataFrame()
            return self._parse_response(raw_text, parser, chain)
        return await self._context.cache.get_or_fetch(
            key,
            lambda: self._fetch_and_parse(url, params, headers, parser, chain),
            max_age=max_age,
            force_update=force_update,
        )

    def _parse_response(
        self,
        raw_text: str,
        parser: BaseParser | None,
        chain: ProviderChain | None,
    ) -> pl.DataFrame:
        if chain is not None:
            # execute() raises UpstreamStructureChangedError if all strategies fail;
            # no None check needed here.
            result = chain.execute(raw_text)
            return result.df

        if parser is not None:
            auto_chain = _build_default_chain(parser)
            if auto_chain is not None:
                try:
                    result = auto_chain.execute(raw_text)
                    return result.df
                except Exception:
                    # Auto-chain failed; fall through to the legacy parser path.
                    pass
            return parser.parse(raw_text)

        return pl.read_csv(io.BytesIO(raw_text.encode("utf-8")), null_values="NULL")

    async def _fetch_and_parse(
        self,
        url: str,
        params: Mapping[str, object] | None,
        headers: Mapping[str, str] | None,
        parser: BaseParser | None,
        chain: ProviderChain | None,
    ) -> pl.DataFrame:
        raw_text = await self._context.http.get_text(url, params=params, headers=headers)
        if not raw_text:
            return pl.DataFrame()
        return self._parse_response(raw_text, parser, chain)

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

        if not use_cache:
            html = await self._context.http.get_text(url, headers=headers)
            return BRefSplitsParser(playerid, year, pitching).parse(html)

        async def fetch_splits_raw() -> pl.DataFrame:
            html = await self._context.http.get_text(url, headers=headers)
            return pl.DataFrame({"html": [html]})

        html_df = await self._context.cache.get_or_fetch(
            key,
            fetch_splits_raw,
            max_age=max_age,
            force_update=force_update,
        )
        html = html_df["html"][0] if html_df.height > 0 and "html" in html_df.columns else ""
        return BRefSplitsParser(playerid, year, pitching).parse(html)
