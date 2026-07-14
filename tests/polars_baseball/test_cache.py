import asyncio
import threading
import weakref
from datetime import timedelta
from pathlib import Path

import polars as pl
import pytest

from polars_baseball._cache import FileCacheAdapter, cached, configure_cache, generate_cache_key, global_cache


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
    key2 = generate_cache_key(url, {"b": 2, "a": "1"})  # sorted params

    assert key1 == key2
    assert isinstance(key1, str)
    assert len(key1) == 32  # MD5 length


def test_file_cache_adapter_get_set(tmp_path: Path) -> None:
    adapter = FileCacheAdapter(cache_dir=tmp_path)
    key = "test_key"

    df = pl.DataFrame({"col1": [1, 2], "col2": ["a", "b"]})

    # Cache miss
    assert adapter.get(key) is None

    # Set cache
    adapter.set(key, df)

    # Cache hit
    cached_df = adapter.get(key)
    assert cached_df is not None
    assert cached_df.equals(df)

    # Clear cache
    adapter.clear()
    assert adapter.get(key) is None


def test_configure_cache_keeps_global_proxy(tmp_path: Path) -> None:
    original_cache = global_cache
    cache_dir = tmp_path / "configured-cache"

    configure_cache(cache_dir)

    assert global_cache is original_cache
    assert global_cache.cache_dir == cache_dir


def test_cache_get_list_set_list(tmp_path: Path) -> None:
    """Standings tables all share the same schema; list cache targets that use case."""
    adapter = FileCacheAdapter(cache_dir=tmp_path)
    key = "list-key"
    dfs = [
        pl.DataFrame({"Tm": ["LAA"], "W": [90]}),
        pl.DataFrame({"Tm": ["NYY"], "W": [95]}),
    ]

    assert adapter.get_list(key) is None

    adapter.set_list(key, dfs)
    restored = adapter.get_list(key)
    assert restored is not None
    assert len(restored) == 2
    assert restored[0].equals(dfs[0])
    assert restored[1].equals(dfs[1])


def test_cache_get_list_empty(tmp_path: Path) -> None:
    adapter = FileCacheAdapter(cache_dir=tmp_path)
    adapter.set_list("empty", [])
    result = adapter.get_list("empty")
    assert result is not None
    assert result == []


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
    async def fetch(ctx: _MemoryContext) -> pl.DataFrame:
        nonlocal calls
        calls += 1
        await asyncio.sleep(0)
        return pl.DataFrame({"value": [calls]})

    results = await asyncio.gather(fetch(context), fetch(context), fetch(context))

    assert calls == 1
    assert all(result.equals(results[0]) for result in results)


@pytest.mark.asyncio
async def _result_a1() -> pl.DataFrame:
    return pl.DataFrame({"a": [1]})


async def _result_a2() -> pl.DataFrame:
    return pl.DataFrame({"a": [2]})


@pytest.mark.asyncio
async def test_cache_get_or_fetch_miss(tmp_path: Path) -> None:
    adapter = FileCacheAdapter(cache_dir=tmp_path)
    df = await adapter.get_or_fetch("k", _result_a1)
    assert df["a"][0] == 1


@pytest.mark.asyncio
async def test_cache_get_or_fetch_hit(tmp_path: Path) -> None:
    adapter = FileCacheAdapter(cache_dir=tmp_path)
    adapter.set("k", pl.DataFrame({"a": [42]}))
    calls = 0

    async def fetch() -> pl.DataFrame:
        nonlocal calls
        calls += 1
        return pl.DataFrame({"a": [calls]})

    df = await adapter.get_or_fetch("k", fetch)
    assert df["a"][0] == 42
    assert calls == 0


@pytest.mark.asyncio
async def test_cache_get_or_fetch_coalesces(tmp_path: Path) -> None:
    adapter = FileCacheAdapter(cache_dir=tmp_path)
    calls = 0

    async def slow_fetch() -> pl.DataFrame:
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.05)
        return pl.DataFrame({"v": [calls]})

    results = await asyncio.gather(
        adapter.get_or_fetch("k", slow_fetch),
        adapter.get_or_fetch("k", slow_fetch),
        adapter.get_or_fetch("k", slow_fetch),
    )

    assert calls == 1
    assert all(r["v"][0] == 1 for r in results)


@pytest.mark.asyncio
async def test_cache_get_or_fetch_force_update(tmp_path: Path) -> None:
    adapter = FileCacheAdapter(cache_dir=tmp_path)
    adapter.set("k", pl.DataFrame({"a": [1]}))
    df = await adapter.get_or_fetch("k", _result_a2, force_update=True)
    assert df["a"][0] == 2


@pytest.mark.asyncio
async def test_cache_get_or_fetch_respects_max_age(tmp_path: Path) -> None:
    adapter = FileCacheAdapter(cache_dir=tmp_path)
    adapter.set("k", pl.DataFrame({"a": [1]}))
    await asyncio.sleep(0.01)
    df = await adapter.get_or_fetch("k", _result_a2, max_age=timedelta(milliseconds=1))
    assert df["a"][0] == 2


async def _async_result(df: pl.DataFrame) -> pl.DataFrame:
    return df


@pytest.mark.asyncio
async def test_in_flight_lock_flat_structure() -> None:
    """_IN_FLIGHT_LOCKS is a flat WeakValueDictionary[str, Lock] keyed by composite string."""
    import gc

    from polars_baseball._cache import _IN_FLIGHT_LOCKS, FileCacheAdapter, _in_flight_lock_for

    cache = FileCacheAdapter()
    lock1 = _in_flight_lock_for(cache, "flat-key")
    assert isinstance(lock1, asyncio.Lock)

    composite = f"{id(cache)}:flat-key"
    assert composite in _IN_FLIGHT_LOCKS

    # Same (cache, key) pair returns the identical lock object.
    lock2 = _in_flight_lock_for(cache, "flat-key")
    assert lock1 is lock2

    # Once the last strong reference is dropped the WeakValueDictionary evicts the entry.
    del lock1, lock2
    gc.collect()
    assert composite not in _IN_FLIGHT_LOCKS


@pytest.mark.asyncio
async def test_in_flight_lock_no_event_loop_key() -> None:
    """The in-flight registry must not use the event loop as a key (old 3-level design)."""
    from polars_baseball._cache import _IN_FLIGHT_LOCKS, FileCacheAdapter, _in_flight_lock_for

    cache = FileCacheAdapter()
    _in_flight_lock_for(cache, "loop-free-key")

    # _IN_FLIGHT_LOCKS is now a flat WeakValueDictionary, not WeakKeyDictionary.
    # WeakKeyDictionary would store AbstractEventLoop objects as keys.
    assert isinstance(_IN_FLIGHT_LOCKS, weakref.WeakValueDictionary)
    assert not isinstance(_IN_FLIGHT_LOCKS, weakref.WeakKeyDictionary)


def test_file_cache_adapter_clear_error(tmp_path: Path) -> None:
    from unittest.mock import patch

    from polars_baseball.exceptions import CacheClearError

    adapter = FileCacheAdapter(cache_dir=tmp_path)

    with patch.object(Path, "iterdir", side_effect=OSError("Permission denied")):
        with pytest.raises(CacheClearError, match="Failed to clear cache"):
            adapter.clear()


def test_shared_exclusive_lock_concurrency() -> None:
    from polars_baseball._cache import SharedExclusiveLock

    lock = SharedExclusiveLock()
    state = []

    with lock.shared():
        with lock.shared():
            state.append("shared-concurrent")

    assert state == ["shared-concurrent"]

    import time

    def run_exclusive() -> None:
        with lock.exclusive():
            state.append("exclusive-acquired")

    with lock.shared():
        t = threading.Thread(target=run_exclusive)
        t.start()
        time.sleep(0.1)
        assert "exclusive-acquired" not in state

    t.join(timeout=2)
    assert "exclusive-acquired" in state


def test_file_cache_adapter_set_os_error_cleanup(tmp_path: Path) -> None:
    """When FileCacheAdapter.set encounters an OSError, it should clean up tmp files and raise."""
    from unittest.mock import patch

    adapter = FileCacheAdapter(cache_dir=tmp_path)
    key = "failing-key"
    df = pl.DataFrame({"a": [1]})

    with patch.object(pl.DataFrame, "write_parquet", side_effect=OSError("Disk full")):
        with pytest.raises(OSError, match="Disk full"):
            adapter.set(key, df)

    # Verify no temp files exist in the cache directory
    tmp_files = list(tmp_path.glob("*.tmp"))
    assert len(tmp_files) == 0
    # Target file should not have been created
    assert not adapter._get_path(key).exists()
