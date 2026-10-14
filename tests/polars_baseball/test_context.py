from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from polars_baseball._cache import CacheAdapter, FileCacheAdapter, NullCacheAdapter
from polars_baseball._client import HttpClient
from polars_baseball.context import BaseballClient, BaseballContext, cleanup


def test_baseball_client_alias() -> None:
    assert BaseballContext is BaseballClient


def test_baseball_client_defaults() -> None:
    client = BaseballClient()
    assert isinstance(client.http, HttpClient)
    assert isinstance(client.cache, CacheAdapter)


def test_baseball_client_with_file_cache(tmp_path: Path) -> None:
    client = BaseballClient.with_file_cache(tmp_path)
    assert isinstance(client.http, HttpClient)
    assert isinstance(client.cache, FileCacheAdapter)
    assert client.cache.cache_dir == tmp_path


def test_baseball_client_with_null_cache() -> None:
    client = BaseballClient.with_null_cache()
    assert isinstance(client.http, HttpClient)
    assert isinstance(client.cache, NullCacheAdapter)


def test_baseball_client_injection() -> None:
    mock_http = MagicMock(spec=HttpClient)
    mock_cache = MagicMock(spec=CacheAdapter)
    client = BaseballClient(http=mock_http, cache=mock_cache)
    assert client.http is mock_http
    assert client.cache is mock_cache


def test_default_returns_shared_instance() -> None:
    ctx1 = BaseballClient.default()
    ctx2 = BaseballClient.default()
    assert ctx1 is ctx2
    assert isinstance(ctx1, BaseballClient)


def test_reset_default_clears_singleton() -> None:
    ctx1 = BaseballClient.default()
    BaseballClient.reset_default()
    ctx2 = BaseballClient.default()
    assert ctx1 is not ctx2


@pytest.mark.asyncio
async def test_cleanup_with_explicit_client() -> None:
    mock_http = AsyncMock(spec=HttpClient)
    client = BaseballClient(http=mock_http)

    await cleanup(client)

    mock_http.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_cleanup_without_arg_closes_default_singleton() -> None:
    client = BaseballClient.default()
    mock_http = AsyncMock(spec=HttpClient)
    client.http = mock_http

    await cleanup()

    mock_http.close.assert_awaited_once()
    assert BaseballClient._default_instance is None


@pytest.mark.asyncio
async def test_client_close_closes_http_client() -> None:
    mock_http = AsyncMock(spec=HttpClient)
    client = BaseballClient(http=mock_http)

    await client.close()

    mock_http.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_context_manager() -> None:
    mock_http = AsyncMock(spec=HttpClient)
    async with BaseballClient(http=mock_http) as client:
        assert client.http is mock_http

    mock_http.close.assert_awaited_once()


@pytest.mark.asyncio
async def test_context_aexit_preserves_exception() -> None:
    client = BaseballClient()
    client.http = AsyncMock()
    client.http.close.side_effect = RuntimeError("Close failed")

    with pytest.raises(ValueError, match="Original error"):
        async with client:
            raise ValueError("Original error")


@pytest.mark.asyncio
async def test_context_aexit_does_not_swallow_keyboard_interrupt() -> None:
    client = BaseballClient()
    client.http = AsyncMock()
    client.http.close.side_effect = KeyboardInterrupt()

    with pytest.raises(KeyboardInterrupt):
        async with client:
            raise ValueError("Original error")
