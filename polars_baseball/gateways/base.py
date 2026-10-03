"""Base class for external data source gateways."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from datetime import timedelta

import polars as pl

from polars_baseball._cache import generate_cache_key
from polars_baseball.context import BaseballContext
from polars_baseball.exceptions import UpstreamUnavailableError


class BaseGateway:
    """Base gateway handling common HTTP fetch, caching, and parsing lifecycles."""

    def __init__(self, context: BaseballContext) -> None:
        self._context = context

    async def _fetch_cached_df(
        self,
        url: str,
        params: Mapping[str, object] | None,
        parser: Callable[[str], pl.DataFrame],
        *,
        headers: Mapping[str, str] | None = None,
        use_cache: bool = True,
        max_age: timedelta | None = None,
        force_update: bool = False,
        error_msg: str = "Upstream service returned empty response.",
        cache_key: str | None = None,
    ) -> pl.DataFrame:
        key = cache_key or generate_cache_key(url, params)

        async def _fetch_and_parse() -> pl.DataFrame:
            if headers is not None:
                raw_text = await self._context.http.get_text(url, params=params, headers=headers)
            else:
                raw_text = await self._context.http.get_text(url, params=params)
            if not raw_text:
                raise UpstreamUnavailableError(error_msg)
            return parser(raw_text)

        if not use_cache:
            return await _fetch_and_parse()

        return await self._context.cache.get_or_fetch(
            key,
            _fetch_and_parse,
            max_age=max_age,
            force_update=force_update,
        )

    async def _fetch_cached_raw(
        self,
        url: str,
        params: Mapping[str, object] | None = None,
        *,
        headers: Mapping[str, str] | None = None,
        use_cache: bool = True,
        max_age: timedelta | None = None,
        force_update: bool = False,
        error_msg: str = "Upstream service returned empty response.",
        cache_key: str | None = None,
    ) -> str:
        key = cache_key or generate_cache_key(url, params)

        async def _fetch() -> str:
            if headers is not None:
                raw_text = await self._context.http.get_text(url, params=params, headers=headers)
            else:
                raw_text = await self._context.http.get_text(url, params=params)
            if not raw_text:
                raise UpstreamUnavailableError(error_msg)
            return raw_text

        if not use_cache:
            return await _fetch()

        raw_bytes = await self._context.cache.get_or_fetch_raw(
            key,
            _fetch,
            max_age=max_age,
            force_update=force_update,
        )
        result = raw_bytes.decode("utf-8") if isinstance(raw_bytes, bytes) else str(raw_bytes)
        if not result:
            raise UpstreamUnavailableError(error_msg)
        return result
