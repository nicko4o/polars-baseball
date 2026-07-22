import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from polars_baseball._cache import CacheAdapter, FileCacheAdapter, global_cache
from polars_baseball._client import HttpClient
from polars_baseball.context import BaseballContext, cleanup


@pytest.fixture(autouse=False)
def reset_default():
    BaseballContext._default_instance = None
    yield
    BaseballContext._default_instance = None


def test_baseball_context_defaults() -> None:
    ctx = BaseballContext()
    assert isinstance(ctx.http, HttpClient)
    assert isinstance(ctx.cache, CacheAdapter)
    assert ctx.cache is global_cache


def test_baseball_context_with_file_cache(tmp_path: Path) -> None:
    ctx = BaseballContext.with_file_cache(tmp_path)
    assert isinstance(ctx.http, HttpClient)
    assert isinstance(ctx.cache, FileCacheAdapter)
    assert ctx.cache.cache_dir == tmp_path


def test_baseball_context_injection() -> None:
    mock_http = MagicMock(spec=HttpClient)
    mock_cache = MagicMock(spec=CacheAdapter)
    ctx = BaseballContext(http=mock_http, cache=mock_cache)
    assert ctx.http is mock_http
    assert ctx.cache is mock_cache


@pytest.mark.usefixtures("reset_default")
def test_default_singleton() -> None:
    ctx1 = BaseballContext.default()
    ctx2 = BaseballContext.default()
    assert ctx1 is ctx2


@pytest.mark.usefixtures("reset_default")
def test_reset_default() -> None:
    ctx1 = BaseballContext.default()
    BaseballContext.reset_default()
    ctx2 = BaseballContext.default()
    assert ctx2 is not ctx1


@pytest.mark.asyncio
async def test_cleanup_with_explicit_context() -> None:
    mock_http = AsyncMock(spec=HttpClient)
    ctx = BaseballContext(http=mock_http)

    await cleanup(ctx)

    mock_http.close.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.usefixtures("reset_default")
async def test_cleanup_without_arg_closes_default() -> None:
    mock_http = AsyncMock(spec=HttpClient)
    BaseballContext._default_instance = BaseballContext(http=mock_http)

    await cleanup()

    mock_http.close.assert_awaited_once()
    assert BaseballContext._default_instance is None


@pytest.mark.asyncio
async def test_context_close_closes_http_client() -> None:
    mock_http = AsyncMock(spec=HttpClient)
    ctx = BaseballContext(http=mock_http)

    await ctx.close()

    mock_http.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_context_manager() -> None:
    mock_http = AsyncMock(spec=HttpClient)
    async with BaseballContext(http=mock_http) as ctx:
        assert ctx.http is mock_http

    mock_http.close.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.usefixtures("reset_default")
async def test_close_resets_default_if_is_default() -> None:
    mock_http = AsyncMock(spec=HttpClient)
    ctx = BaseballContext(http=mock_http)
    BaseballContext._default_instance = ctx

    await ctx.close()

    assert BaseballContext._default_instance is None
    mock_http.close.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.usefixtures("reset_default")
async def test_cleanup_detaches_default_before_closing() -> None:
    close_started = asyncio.Event()
    allow_close = asyncio.Event()
    mock_http = AsyncMock(spec=HttpClient)

    async def delayed_close() -> None:
        close_started.set()
        await allow_close.wait()

    mock_http.close.side_effect = delayed_close
    ctx = BaseballContext(http=mock_http)
    BaseballContext._default_instance = ctx

    cleanup_task = asyncio.create_task(cleanup(ctx))
    await close_started.wait()

    assert BaseballContext._default_instance is None

    allow_close.set()
    await cleanup_task


@pytest.mark.usefixtures("reset_default")
def test_default_is_baseballcontext_instance() -> None:
    ctx = BaseballContext.default()
    assert isinstance(ctx, BaseballContext)
    assert isinstance(ctx.http, HttpClient)


@pytest.mark.asyncio
async def test_context_aexit_preserves_exception() -> None:
    ctx = BaseballContext()
    ctx.http = AsyncMock()
    ctx.http.close.side_effect = RuntimeError("Close failed")

    with pytest.raises(ValueError, match="Original error"):
        async with ctx:
            raise ValueError("Original error")
