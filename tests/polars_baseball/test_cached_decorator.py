from __future__ import annotations

import asyncio
from datetime import timedelta
from unittest.mock import MagicMock

import polars as pl
import pytest

from polars_baseball._cache import CacheCallArgs, cached
from polars_baseball.context import BaseballContext

_CACHE_MISS_TIMEOUT_SECONDS = 1


@pytest.mark.asyncio
async def test_cached_hit_returns_cached_data_and_skips_fetch() -> None:
    mock_cache = MagicMock()
    cached_df = pl.DataFrame({"x": [1]})
    mock_cache.get.return_value = cached_df
    fetch_called = False

    async def fetch() -> pl.DataFrame:
        nonlocal fetch_called
        fetch_called = True
        return pl.DataFrame({"x": [1]})

    @cached(key="test-key", max_age=timedelta(hours=1))
    async def query(context: BaseballContext | None = None) -> pl.DataFrame:
        return await fetch()

    mock_ctx = BaseballContext(cache=mock_cache)
    result = await query(context=mock_ctx)

    assert result.equals(cached_df)
    assert not fetch_called
    mock_cache.get.assert_called_once_with("test-key", max_age=timedelta(hours=1))


@pytest.mark.asyncio
async def test_cached_miss_calls_fetch_and_stores() -> None:
    mock_cache = MagicMock()
    mock_cache.get.return_value = None
    expected_df = pl.DataFrame({"x": [2]})

    @cached(key="test-key")
    async def query(context: BaseballContext | None = None) -> pl.DataFrame:
        return expected_df

    mock_ctx = BaseballContext(cache=mock_cache)
    result = await asyncio.wait_for(query(context=mock_ctx), timeout=_CACHE_MISS_TIMEOUT_SECONDS)

    assert result.equals(expected_df)
    mock_cache.set.assert_called_once_with("test-key", expected_df)


@pytest.mark.asyncio
async def test_cached_with_dynamic_key() -> None:
    mock_cache = MagicMock()
    mock_cache.get.return_value = None

    def cache_key(call: CacheCallArgs) -> str:
        year = call.argument("year", int)
        team = call.argument("team", str)
        return f"standings-{year}-{team}"

    @cached(key=cache_key)
    async def query(year: int, team: str, context: BaseballContext | None = None) -> pl.DataFrame:
        return pl.DataFrame({"year": [year], "team": [team]})

    mock_ctx = BaseballContext(cache=mock_cache)
    result = await query(2026, "BOS", context=mock_ctx)

    assert result["year"][0] == 2026
    assert result["team"][0] == "BOS"
    mock_cache.get.assert_called_once_with("standings-2026-BOS", max_age=None)
    mock_cache.set.assert_called_once()


@pytest.mark.asyncio
async def test_cached_stores_empty_dataframe() -> None:
    mock_cache = MagicMock()
    mock_cache.get.return_value = None

    @cached(key="empty-key")
    async def query(context: BaseballContext | None = None) -> pl.DataFrame:
        return pl.DataFrame()

    mock_ctx = BaseballContext(cache=mock_cache)
    result = await query(context=mock_ctx)

    assert result.is_empty()
    mock_cache.set.assert_called_once_with("empty-key", result)


@pytest.mark.asyncio
async def test_cached_key_function_error_is_not_swallowed() -> None:
    mock_cache = MagicMock()

    def broken_key(_call: CacheCallArgs) -> str:
        raise RuntimeError("broken cache key")

    @cached(key=broken_key)
    async def query(context: BaseballContext | None = None) -> pl.DataFrame:
        return pl.DataFrame({"x": [1]})

    mock_ctx = BaseballContext(cache=mock_cache)

    with pytest.raises(RuntimeError, match="broken cache key"):
        await query(context=mock_ctx)

    mock_cache.get.assert_not_called()


@pytest.mark.asyncio
async def test_cached_dynamic_max_age() -> None:
    mock_cache = MagicMock()
    mock_cache.get.return_value = None

    def max_age_resolver(call: CacheCallArgs) -> timedelta | None:
        year = call.argument("year", int)
        return timedelta(days=1) if year == 2026 else None

    @cached(key="test-key", max_age=max_age_resolver)
    async def query(year: int, context: BaseballContext | None = None) -> pl.DataFrame:
        return pl.DataFrame({"year": [year]})

    mock_ctx = BaseballContext(cache=mock_cache)

    await query(2026, context=mock_ctx)
    mock_cache.get.assert_called_with("test-key", max_age=timedelta(days=1))

    await query(2025, context=mock_ctx)
    mock_cache.get.assert_called_with("test-key", max_age=None)


@pytest.mark.asyncio
async def test_cached_force_update() -> None:
    mock_cache = MagicMock()
    mock_cache.get.return_value = pl.DataFrame({"x": [10]})
    fetch_calls = 0

    @cached(key="force-key")
    async def query(force_update: bool = False, context: BaseballContext | None = None) -> pl.DataFrame:
        nonlocal fetch_calls
        fetch_calls += 1
        return pl.DataFrame({"x": [20]})

    mock_ctx = BaseballContext(cache=mock_cache)

    res1 = await query(force_update=False, context=mock_ctx)
    assert res1["x"][0] == 10
    assert fetch_calls == 0

    res2 = await query(force_update=True, context=mock_ctx)
    assert res2["x"][0] == 20
    assert fetch_calls == 1
    mock_cache.set.assert_called_with("force-key", res2)


@pytest.mark.asyncio
async def test_cached_dynamic_key_receives_cache_call_args() -> None:
    mock_cache = MagicMock()
    mock_cache.get.return_value = None

    def key_for_year(call: CacheCallArgs) -> str:
        assert call.context.cache is mock_cache
        assert not call.force_update
        year = call.argument("year", int)
        return f"year-{year}"

    @cached(key=key_for_year)
    async def query(year: int, team: str, context: BaseballContext | None = None) -> pl.DataFrame:
        return pl.DataFrame({"year": [year], "team": [team]})

    await query(2026, "BOS", context=BaseballContext(cache=mock_cache))

    mock_cache.get.assert_called_once_with("year-2026", max_age=None)


@pytest.mark.asyncio
async def test_cached_dynamic_key_reads_named_arguments() -> None:
    mock_cache = MagicMock()
    mock_cache.get.return_value = None

    def key_for_call(call: CacheCallArgs) -> str:
        year = call.argument("year", int)
        team = call.argument("team", str)
        return f"{year}-{team}"

    @cached(key=key_for_call)
    async def query(year: int, team: str, context: BaseballContext | None = None) -> pl.DataFrame:
        return pl.DataFrame({"year": [year], "team": [team]})

    await query(2026, "BOS", context=BaseballContext(cache=mock_cache))

    mock_cache.get.assert_called_once_with("2026-BOS", max_age=None)


@pytest.mark.asyncio
async def test_cached_dynamic_key_uses_context_from_cache_call_args() -> None:
    mock_cache = MagicMock()
    mock_cache.get.return_value = None

    def key_for_context(call: CacheCallArgs) -> str:
        assert call.context.cache is mock_cache
        year = call.argument("year", int)
        return f"context-{year}"

    @cached(key=key_for_context)
    async def query(year: int, context: BaseballContext | None = None) -> pl.DataFrame:
        return pl.DataFrame({"year": [year]})

    await query(2026, context=BaseballContext(cache=mock_cache))

    mock_cache.get.assert_called_once_with("context-2026", max_age=None)


@pytest.mark.asyncio
async def test_cached_dynamic_max_age_uses_context_from_cache_call_args() -> None:
    mock_cache = MagicMock()
    mock_cache.get.return_value = None

    def max_age_for_context(call: CacheCallArgs) -> timedelta:
        assert call.context.cache is mock_cache
        return timedelta(minutes=5)

    @cached(key="context-max-age", max_age=max_age_for_context)
    async def query(context: BaseballContext | None = None) -> pl.DataFrame:
        return pl.DataFrame({"x": [1]})

    await query(context=BaseballContext(cache=mock_cache))

    mock_cache.get.assert_called_once_with("context-max-age", max_age=timedelta(minutes=5))


@pytest.mark.asyncio
async def test_cached_rejects_context_parameter_without_cache_attribute() -> None:
    @cached(key="bad-context")
    async def query(context: object) -> pl.DataFrame:
        return pl.DataFrame({"x": [1]})

    with pytest.raises(TypeError, match="context must expose a cache attribute"):
        await query(context=object())


@pytest.mark.asyncio
async def test_cached_no_longer_treats_ctx_alias_as_cache_context() -> None:
    mock_cache = MagicMock()
    mock_cache.get.return_value = pl.DataFrame({"x": [3]})

    @cached(key="alias-key")
    async def query(ctx: BaseballContext | None = None) -> pl.DataFrame:
        return pl.DataFrame({"x": [4]})

    result = await query(ctx=BaseballContext(cache=mock_cache))

    assert result["x"][0] == 4
    mock_cache.get.assert_not_called()
