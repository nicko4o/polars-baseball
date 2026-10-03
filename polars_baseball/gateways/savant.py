import asyncio
import json
from collections.abc import Callable

import polars as pl

from polars_baseball._cache import generate_cache_key
from polars_baseball._encoding import ensure_str
from polars_baseball.context import BaseballContext
from polars_baseball.exceptions import UpstreamParseError
from polars_baseball.gateways.base import BaseGateway
from polars_baseball.parsers.savant import SavantCSVParser, parse_savant_leaderboard
from polars_baseball.parsers.savant_gamefeed import JsonObject

_GAMEFEED_DATASET_PARAM = "__dataset__"
_ERROR_SCAN_LIMIT = 200

GamefeedParser = Callable[[int, JsonObject], pl.DataFrame]


class SavantGateway(BaseGateway):
    """Gateway for querying and caching raw data from Baseball Savant."""

    def __init__(self, context: BaseballContext) -> None:
        super().__init__(context)
        self._csv_parser = SavantCSVParser()

    async def get_dataset(
        self,
        url: str,
        params: dict[str, str] | None = None,
        *,
        use_cache: bool = True,
    ) -> pl.DataFrame:
        """Universal loader for Savant datasets (search endpoints, raw CSV)."""

        def _parse(raw: str) -> pl.DataFrame:
            self._verify_error_response(raw)
            return self._csv_parser.parse(raw)

        return await self._fetch_cached_df(
            url,
            params,
            parser=_parse,
            use_cache=use_cache,
            error_msg="Savant returned empty response.",
        )

    async def get_leaderboard(
        self,
        url: str,
        params: dict[str, str] | None = None,
    ) -> pl.DataFrame:
        """Fetch a leaderboard dataset with multi-format parsing (CSV → embedded JSON → HTML table)."""

        def _parse(raw: str) -> pl.DataFrame:
            return parse_savant_leaderboard(raw)

        return await self._fetch_cached_df(
            url,
            params,
            parser=_parse,
            error_msg="Savant returned empty response.",
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

        def _parse(raw_json: str) -> pl.DataFrame:
            try:
                payload = json.loads(ensure_str(raw_json))
            except json.JSONDecodeError as exc:
                raise UpstreamParseError("Savant gamefeed did not return valid JSON.") from exc

            if not isinstance(payload, dict):
                raise UpstreamParseError("Savant gamefeed JSON root must be an object.")
            return parser(game_pk, payload)

        return await self._fetch_cached_df(
            url,
            params,
            parser=_parse,
            use_cache=use_cache,
            cache_key=key,
            error_msg="Savant gamefeed returned empty response.",
        )

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
        return self._csv_parser.parse(raw)

    def _verify_error_response(self, raw_data: str | bytes) -> None:
        """Inspect response for upstream errors reported as CSV error rows."""
        from polars_baseball._encoding import ensure_bytes

        raw_bin = ensure_bytes(raw_data)
        if b"error" not in raw_bin[:_ERROR_SCAN_LIMIT]:
            return

        try:
            df_err = pl.read_csv(raw_bin)
        except pl.exceptions.PolarsError:
            raise UpstreamParseError("Savant request failed with an error row.") from None

        if "error" in df_err.columns and df_err.height > 0:
            raise UpstreamParseError(str(df_err["error"][0]))
        raise UpstreamParseError("Savant request failed with an error row.")
