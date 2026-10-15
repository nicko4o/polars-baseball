import json
from collections.abc import Callable, Mapping
from datetime import timedelta
from typing import cast

import polars as pl

from polars_baseball._cache import generate_cache_key
from polars_baseball._json_utils import JsonObject
from polars_baseball.client import BaseballClient
from polars_baseball.exceptions import PolarsBaseballHttpError, UpstreamParseError
from polars_baseball.gateways.base import BaseGateway


class MlbStatsGateway(BaseGateway):
    """Gateway for MLB Stats API JSON payloads."""

    def __init__(self, context: BaseballClient) -> None:
        super().__init__(context)

    async def fetch(
        self,
        url: str,
        params: Mapping[str, object] | None,
        error_msg: str,
        parser: Callable[[JsonObject], pl.DataFrame],
        *,
        use_cache: bool = True,
        max_age: timedelta | None = None,
        force_update: bool = False,
        cache_key: str | None = None,
    ) -> pl.DataFrame:
        key = cache_key or generate_cache_key(url, params)

        async def _fetch_and_parse() -> pl.DataFrame:
            result = await self._fetch_json(url, params, error_msg)
            if not isinstance(result, dict):
                raise UpstreamParseError(f"Expected dict from API response, got {type(result)}")
            try:
                return parser(cast(JsonObject, result))
            except (KeyError, TypeError, ValueError, pl.exceptions.PolarsError) as exc:
                raise UpstreamParseError(f"{error_msg}: {exc}") from exc

        if not use_cache:
            return await _fetch_and_parse()

        return await self._context.cache.get_or_fetch(
            key,
            _fetch_and_parse,
            max_age=max_age,
            force_update=force_update,
        )

    async def fetch_payload(
        self,
        url: str,
        params: Mapping[str, object] | None,
        error_msg: str,
        parser: Callable[[object], pl.DataFrame],
        *,
        use_cache: bool = True,
        max_age: timedelta | None = None,
        force_update: bool = False,
        cache_key: str | None = None,
    ) -> pl.DataFrame:
        key = cache_key or generate_cache_key(url, params)

        async def _fetch_and_parse() -> pl.DataFrame:
            result = await self._fetch_json(url, params, error_msg)
            try:
                return parser(result)
            except (KeyError, TypeError, ValueError, pl.exceptions.PolarsError) as exc:
                raise UpstreamParseError(f"{error_msg}: {exc}") from exc

        if not use_cache:
            return await _fetch_and_parse()

        return await self._context.cache.get_or_fetch(
            key,
            _fetch_and_parse,
            max_age=max_age,
            force_update=force_update,
        )

    async def fetch_text(
        self,
        url: str,
        error_msg: str,
    ) -> str:
        try:
            raw_text = await self._context.http.get_text(url)
        except PolarsBaseballHttpError:
            raise
        except (TypeError, ValueError) as exc:
            raise UpstreamParseError(f"{error_msg}: {exc}") from exc
        if not raw_text:
            raise UpstreamParseError(error_msg)
        return raw_text

    async def _fetch_json(
        self,
        url: str,
        params: Mapping[str, object] | None,
        error_msg: str,
    ) -> object:
        try:
            raw_text = await self._context.http.get_text(url, params=params)
        except PolarsBaseballHttpError:
            raise
        except (TypeError, ValueError) as exc:
            raise UpstreamParseError(f"{error_msg}: {exc}") from exc

        try:
            return json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise UpstreamParseError(f"{error_msg}: {exc}") from exc
