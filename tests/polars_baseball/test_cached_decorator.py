from __future__ import annotations

import asyncio
from datetime import timedelta
from unittest.mock import MagicMock

import polars as pl
import pytest

from polars_baseball._cache import cached
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

    @cached(key=lambda year, team: f"standings-{year}-{team}")
    async def query(year: int, team: str, context: BaseballContext | None = None) -> pl.DataFrame:
        return pl.DataFrame({"year": [year], "team": [team]})

    mock_ctx = BaseballContext(cache=mock_cache)
    result = await query(2026, "BOS", context=mock_ctx)

    assert result["year"][0] == 2026
    assert result["team"][0] == "BOS"
    mock_cache.get.assert_called_once_with("standings-2026-BOS", max_age=None)
    mock_cache.set.assert_called_once()


@pytest.mark.asyncio
async def test_cached_returns_empty_df_on_miss() -> None:
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

    def broken_key() -> str:
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

    def max_age_resolver(year: int, **kwargs: object) -> timedelta | None:
        return timedelta(days=1) if year == 2026 else None

    @cached(key="test-key", max_age=max_age_resolver)
    async def query(year: int, context: BaseballContext | None = None) -> pl.DataFrame:
        return pl.DataFrame({"year": [year]})

    mock_ctx = BaseballContext(cache=mock_cache)

    # 2026 should resolve max_age to 1 day
    await query(2026, context=mock_ctx)
    mock_cache.get.assert_called_with("test-key", max_age=timedelta(days=1))

    # 2025 should resolve max_age to None
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

    # Normal fetch: cache hit, bypass underlying call
    res1 = await query(force_update=False, context=mock_ctx)
    assert res1["x"][0] == 10
    assert fetch_calls == 0

    # Forced update: ignore cache hit, invoke fetch and refresh cache
    res2 = await query(force_update=True, context=mock_ctx)
    assert res2["x"][0] == 20
    assert fetch_calls == 1
    mock_cache.set.assert_called_with("force-key", res2)
