import asyncio
import threading
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

import polars_baseball.context as _ctx_module
from polars_baseball._cache import CacheAdapter, FileCacheAdapter, global_cache
from polars_baseball._client import HttpClient
from polars_baseball.context import BaseballContext, cleanup, default_context


@pytest.fixture(autouse=False)
def isolated_default_ctx():
    """Save and restore the default context singleton around a test."""
    original = _ctx_module._default_ctx
    yield
    _ctx_module._default_ctx = original


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


def test_default_context_is_singleton() -> None:
    ctx1 = default_context()
    ctx2 = default_context()
    assert ctx1 is ctx2


@pytest.mark.asyncio
async def test_cleanup() -> None:
    mock_http = AsyncMock(spec=HttpClient)
    ctx = BaseballContext(http=mock_http)

    await cleanup(ctx)

    mock_http.close.assert_awaited_once()


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


# ---------------------------------------------------------------------------
# New tests covering the two bugs fixed in fix/cache-asyncio-boundary
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@pytest.mark.usefixtures("isolated_default_ctx")
async def test_cleanup_no_arg_resets_default_context() -> None:
    """cleanup() with no argument must clear the singleton so the next call gets a fresh instance."""
    mock_http = AsyncMock(spec=HttpClient)
    _ctx_module._default_ctx = BaseballContext(http=mock_http)

    await cleanup()

    assert _ctx_module._default_ctx is None
    mock_http.close.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.usefixtures("isolated_default_ctx")
async def test_cleanup_with_singleton_resets_it() -> None:
    """Passing the singleton explicitly to cleanup() must also reset the singleton reference."""
    mock_http = AsyncMock(spec=HttpClient)
    singleton = BaseballContext(http=mock_http)
    _ctx_module._default_ctx = singleton

    await cleanup(singleton)

    assert _ctx_module._default_ctx is None
    mock_http.close.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.usefixtures("isolated_default_ctx")
async def test_cleanup_detaches_singleton_before_closing() -> None:
    close_started = asyncio.Event()
    allow_close = asyncio.Event()
    mock_http = AsyncMock(spec=HttpClient)

    async def delayed_close() -> None:
        close_started.set()
        await allow_close.wait()

    mock_http.close.side_effect = delayed_close
    singleton = BaseballContext(http=mock_http)
    _ctx_module._default_ctx = singleton

    cleanup_task = asyncio.create_task(cleanup(singleton))
    await close_started.wait()

    assert default_context() is not singleton

    allow_close.set()
    await cleanup_task


@pytest.mark.asyncio
@pytest.mark.usefixtures("isolated_default_ctx")
async def test_cleanup_with_non_singleton_does_not_reset_singleton() -> None:
    """cleanup() with a non-singleton context must not touch the singleton."""
    mock_singleton_http = AsyncMock(spec=HttpClient)
    singleton = BaseballContext(http=mock_singleton_http)
    _ctx_module._default_ctx = singleton

    mock_other_http = AsyncMock(spec=HttpClient)
    other_ctx = BaseballContext(http=mock_other_http)
    await cleanup(other_ctx)

    # Singleton is untouched; only other_ctx was closed.
    assert _ctx_module._default_ctx is singleton
    mock_singleton_http.close.assert_not_awaited()
    mock_other_http.close.assert_awaited_once()


@pytest.mark.usefixtures("isolated_default_ctx")
def test_default_context_thread_safety() -> None:
    """Concurrent calls to default_context() must all return the exact same instance."""
    _ctx_module._default_ctx = None

    results: list[BaseballContext] = []
    barrier = threading.Barrier(20)
    result_lock = threading.Lock()

    def grab() -> None:
        barrier.wait()  # All threads start at the same time to maximize contention.
        ctx = default_context()
        with result_lock:
            results.append(ctx)

    threads = [threading.Thread(target=grab) for _ in range(20)]
    for t in threads:
        t.start()
    for t in threads:
        t.join(timeout=5)

    assert len(results) == 20
    first = results[0]
    assert all(r is first for r in results)


@pytest.mark.asyncio
@pytest.mark.usefixtures("isolated_default_ctx")
async def test_context_manager_resets_singleton_on_exit() -> None:
    """Using 'async with' on the singleton must reset _default_ctx when exiting."""
    mock_http = AsyncMock(spec=HttpClient)
    singleton = BaseballContext(http=mock_http)
    _ctx_module._default_ctx = singleton

    async with singleton:
        pass

    assert _ctx_module._default_ctx is None
    mock_http.close.assert_awaited_once()
