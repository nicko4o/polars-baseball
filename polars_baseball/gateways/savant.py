import asyncio
import json
from collections.abc import Callable

import polars as pl

from polars_baseball._cache import generate_cache_key
from polars_baseball._encoding import ensure_str
from polars_baseball.context import BaseballContext
from polars_baseball.exceptions import UpstreamParseError, UpstreamUnavailableError
from polars_baseball.parsers._strategy import ProviderChain
from polars_baseball.parsers.savant import SavantCSVParser
from polars_baseball.parsers.savant_gamefeed import JsonObject
from polars_baseball.parsers.savant_leaderboard_strategy import (
    SavantCSVStrategy,
    SavantHTMLTableStrategy,
)

_GAMEFEED_DATASET_PARAM = "__dataset__"
_ERROR_SCAN_LIMIT = 200

GamefeedParser = Callable[[int, JsonObject], pl.DataFrame]

_DEFAULT_LEADERBOARD_CHAIN: ProviderChain | None = None


def _get_leaderboard_chain() -> ProviderChain:
    global _DEFAULT_LEADERBOARD_CHAIN
    if _DEFAULT_LEADERBOARD_CHAIN is None:
        _DEFAULT_LEADERBOARD_CHAIN = ProviderChain([SavantCSVStrategy(), SavantHTMLTableStrategy()])
    return _DEFAULT_LEADERBOARD_CHAIN


class SavantGateway:
    """Gateway for querying and caching raw data from Baseball Savant."""

    def __init__(self, context: BaseballContext) -> None:
        self._context = context
        self._csv_parser = SavantCSVParser()

    async def get_dataset(
        self,
        url: str,
        params: dict[str, str] | None = None,
        *,
        use_cache: bool = True,
        raise_on_empty: bool = False,
    ) -> pl.DataFrame:
        """Universal loader for Savant datasets (search endpoints, raw CSV)."""
        key = generate_cache_key(url, params)
        if not use_cache:
            return await self._fetch_and_parse(url, params, raise_on_empty)
        return await self._context.cache.get_or_fetch(
            key,
            lambda: self._fetch_and_parse(url, params, raise_on_empty),
        )

    async def get_leaderboard(
        self,
        url: str,
        params: dict[str, str] | None = None,
    ) -> pl.DataFrame:
        """Fetch a leaderboard dataset with ProviderChain degradation (CSV → HTML)."""
        key = generate_cache_key(url, params)
        return await self._context.cache.get_or_fetch(
            key,
            lambda: self._fetch_and_parse_leaderboard(url, params),
        )

    async def get_optional_dataset(
        self,
        url: str,
        params: dict[str, str] | None = None,
    ) -> pl.DataFrame | None:
        """Return a cached CSV dataset, or None when the endpoint is unavailable."""
        key = generate_cache_key(url, params)
        cached = await asyncio.to_thread(self._context.cache.get, key)
        if cached is not None:
            return cached

        result = await self._fetch_optional_dataset(url, params)
        if result is None:
            return None
        await asyncio.to_thread(self._context.cache.set, key, result)
        return result

    async def get_gamefeed_dataset(
        self,
        url: str,
        game_pk: int,
        dataset_name: str,
        parser: GamefeedParser,
        *,
        use_cache: bool = True,
    ) -> pl.DataFrame:
        """Fetch a Baseball Savant gamefeed JSON node as a cached DataFrame."""
        params = {"game_pk": str(game_pk)}
        cache_params = {**params, _GAMEFEED_DATASET_PARAM: dataset_name}
        key = generate_cache_key(url, cache_params)
        if not use_cache:
            return await self._fetch_and_parse_gamefeed(url, params, game_pk, parser)
        return await self._context.cache.get_or_fetch(
            key,
            lambda: self._fetch_and_parse_gamefeed(url, params, game_pk, parser),
        )

    async def _fetch_and_parse(
        self,
        url: str,
        params: dict[str, str] | None,
        raise_on_empty: bool,
    ) -> pl.DataFrame:
        raw = await self._context.http.get_text(url, params=params)
        if not raw:
            raise UpstreamUnavailableError("Savant returned empty response.")

        raw_text = ensure_str(raw)
        self._verify_error_response(raw_text)
        return self._csv_parser.parse(raw_text)

    async def _fetch_optional_dataset(
        self,
        url: str,
        params: dict[str, str] | None,
    ) -> pl.DataFrame | None:
        raw = await self._context.http.get_text(url, params=params)
        if not raw:
            return None
        raw_text = ensure_str(raw)
        if "<html" in raw_text.lower():
            return None
        return self._csv_parser.parse(raw_text)

    async def _fetch_and_parse_leaderboard(
        self,
        url: str,
        params: dict[str, str] | None,
    ) -> pl.DataFrame:
        raw = await self._context.http.get_text(url, params=params)
        if not raw:
            raise UpstreamUnavailableError("Savant returned empty response.")

        raw_text = ensure_str(raw)
        chain = _get_leaderboard_chain()
        result = chain.execute(raw_text)
        return result.df

    async def _fetch_and_parse_gamefeed(
        self,
        url: str,
        params: dict[str, str],
        game_pk: int,
        parser: GamefeedParser,
    ) -> pl.DataFrame:
        raw_json = await self._context.http.get_text(url, params=params)
        if not raw_json:
            raise UpstreamUnavailableError("Savant gamefeed returned empty response.")

        try:
            payload = json.loads(ensure_str(raw_json))
        except json.JSONDecodeError as exc:
            raise UpstreamParseError("Savant gamefeed did not return valid JSON.") from exc

        if not isinstance(payload, dict):
            raise UpstreamParseError("Savant gamefeed JSON root must be an object.")
        return parser(game_pk, payload)

    def _verify_error_response(self, raw_text: str) -> None:
        """Inspect response for upstream errors reported as CSV error rows.

        Only used by the legacy get_dataset path; the ProviderChain in
        get_leaderboard handles errors through its probe mechanism.
        """
        import io

        from polars_baseball._encoding import ensure_bytes

        if "error" not in raw_text[:_ERROR_SCAN_LIMIT]:
            return

        raw_bin = ensure_bytes(raw_text)
        try:
            df_err = pl.read_csv(io.BytesIO(raw_bin))
        except pl.exceptions.PolarsError:
            raise UpstreamParseError("Savant request failed with an error row.") from None

        if "error" in df_err.columns and df_err.height > 0:
            raise UpstreamParseError(str(df_err["error"][0]))
        raise UpstreamParseError("Savant request failed with an error row.")
