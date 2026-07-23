import asyncio
import threading
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

import polars as pl
import pytest

from polars_baseball._cache import (
    FileCacheAdapter,
    GlobalCache,
    NullCacheAdapter,
    _in_flight_lock_for,
    cached,
    configure_cache,
    generate_cache_key,
    global_cache,
)


class _MemoryCache:
    def __init__(self) -> None:
        self.value: pl.DataFrame | None = None

    def get(self, key: str, max_age: timedelta | None = None) -> pl.DataFrame | None:
        return self.value

    def set(self, key: str, value: pl.DataFrame) -> None:
        self.value = value

    def clear(self) -> None:
        self.value = None


class _MemoryContext:
    def __init__(self) -> None:
        self.cache = _MemoryCache()


def test_generate_cache_key() -> None:
    url = "https://example.com/api"
    params = {"a": "1", "b": 2}

    key1 = generate_cache_key(url, params)
    key2 = generate_cache_key(url, {"b": 2, "a": "1"})

    assert key1 == key2
    assert isinstance(key1, str)
    assert len(key1) == 32


def test_file_cache_adapter_get_set(tmp_path: Path) -> None:
    adapter = FileCacheAdapter(cache_dir=tmp_path)
    key = "test_key"

    df = pl.DataFrame({"col1": [1, 2], "col2": ["a", "b"]})

    assert adapter.get(key) is None

    adapter.set(key, df)

    cached_df = adapter.get(key)
    assert cached_df is not None
    assert cached_df.equals(df)

    adapter.clear()
    assert adapter.get(key) is None


def test_null_cache_adapter_never_stores_values() -> None:
    adapter = NullCacheAdapter()
    df = pl.DataFrame({"col1": [1]})

    adapter.set("key", df)

    assert adapter.get("key") is None


def test_global_cache_starts_as_noop_when_explicitly_configured() -> None:
    adapter = GlobalCache(use_null_default=True)
    df = pl.DataFrame({"col1": [1]})

    adapter.set("key", df)

    assert adapter.get("key") is None
    with pytest.raises(RuntimeError, match="not configured"):
        _ = adapter.cache_dir


def test_global_cache_defaults_to_file_cache() -> None:
    from polars_baseball._config import DEFAULT_CACHE_DIR

    adapter = GlobalCache()
    assert adapter.cache_dir == DEFAULT_CACHE_DIR


@pytest.mark.asyncio
async def test_null_cache_get_or_fetch_runs_every_time() -> None:
    adapter = NullCacheAdapter()
    calls = 0

    async def fetch() -> pl.DataFrame:
        nonlocal calls
        calls += 1
        return pl.DataFrame({"value": [calls]})

    first = await adapter.get_or_fetch("key", fetch)
    second = await adapter.get_or_fetch("key", fetch)

    assert first["value"][0] == 1
    assert second["value"][0] == 2
    assert calls == 2


def test_configure_cache_keeps_global_proxy(tmp_path: Path) -> None:
    original_cache = global_cache
    cache_dir = tmp_path / "configured-cache"

    configure_cache(cache_dir)

    assert global_cache is original_cache
    assert global_cache.cache_dir == cache_dir


def test_file_cache_adapter_concurrent_same_key_writes(tmp_path: Path) -> None:
    adapter = FileCacheAdapter(cache_dir=tmp_path)
    key = "shared-key"
    left = pl.DataFrame({"value": [1, 2, 3]})
    right = pl.DataFrame({"value": [4, 5, 6]})
    threads = [
        threading.Thread(target=adapter.set, args=(key, left)),
        threading.Thread(target=adapter.set, args=(key, right)),
    ]

    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=5)

    cached_df = adapter.get(key)

    assert all(not thread.is_alive() for thread in threads)
    assert cached_df is not None
    assert cached_df.equals(left) or cached_df.equals(right)
    assert not list(tmp_path.glob("*.tmp"))


@pytest.mark.asyncio
async def test_cached_coalesces_concurrent_misses() -> None:
    calls = 0
    context = _MemoryContext()

    @cached("shared-key")
    async def fetch(context: _MemoryContext) -> pl.DataFrame:
        nonlocal calls
        calls += 1
        await asyncio.sleep(0)
        return pl.DataFrame({"value": [calls]})

    results = await asyncio.gather(fetch(context), fetch(context), fetch(context))

    assert calls == 1
    assert all(result.equals(results[0]) for result in results)


@pytest.mark.asyncio
async def test_cached_checks_cache_before_lock() -> None:
    """Cache hits must return before acquiring the in-flight asyncio.Lock."""
    context = _MemoryContext()

    @cached("pre-lock-check-key")
    async def fetch(context: _MemoryContext) -> pl.DataFrame:  # noqa: ARG001
        return pl.DataFrame({"value": [1]})

    await fetch(context)

    with patch("polars_baseball._cache._in_flight_lock_for", wraps=_in_flight_lock_for) as mock_lock:
        df = await fetch(context)

    assert df["value"][0] == 1
    assert mock_lock.call_count == 0, "Lock was acquired before cache check (pre-lock fast path missing)"


def test_file_cache_adapter_set_os_error_cleanup(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """When FileCacheAdapter.set encounters an OSError, it should clean up tmp files, log warning, and disable cache."""
    adapter = FileCacheAdapter(cache_dir=tmp_path)
    assert not adapter._disabled
    key = "failing-key"
    df = pl.DataFrame({"a": [1]})

    with patch.object(pl.DataFrame, "write_parquet", side_effect=OSError("Disk full")):
        adapter.set(key, df)

    assert adapter._disabled
    tmp_files = list(tmp_path.glob("*.tmp"))
    assert len(tmp_files) == 0
    assert not adapter._get_path(key).exists()
    assert "Failed to write cache entry" in caplog.text

    adapter.set("another-key", df)
    assert adapter.get("another-key") is None


def test_file_cache_adapter_init_os_error_defensive(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """When FileCacheAdapter.__init__ fails to mkdir, it disables cache, logs warning, and does not crash."""
    read_only_dir = tmp_path / "read_only"
    with patch.object(Path, "mkdir", side_effect=PermissionError("Read-only file system")):
        adapter = FileCacheAdapter(cache_dir=read_only_dir)

    assert adapter._disabled
    assert adapter.cache_dir == read_only_dir
    assert "Failed to create cache directory" in caplog.text

    adapter.set("k", pl.DataFrame({"a": [1]}))
    assert adapter.get("k") is None
    adapter.clear()


def test_read_cache_memory_error_propagates(tmp_path: Path) -> None:
    adapter = FileCacheAdapter(cache_dir=tmp_path)
    key = "memfail-key"
    adapter.set(key, pl.DataFrame({"a": [1]}))

    with patch("polars_baseball._cache.pl.read_parquet", side_effect=MemoryError("OOM")):
        with pytest.raises(MemoryError):
            adapter.get(key)
