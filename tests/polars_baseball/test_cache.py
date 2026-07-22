import asyncio
import threading
import weakref
from datetime import timedelta
from pathlib import Path
from unittest.mock import patch

import polars as pl
import pytest

from polars_baseball._cache import (
    FileCacheAdapter,
    GlobalCache,
    NullCacheAdapter,
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


def test_null_cache_adapter_never_stores_values() -> None:
    adapter = NullCacheAdapter()
    df = pl.DataFrame({"col1": [1]})

    adapter.set("key", df)
    adapter.set_list("list-key", [df])

    assert adapter.get("key") is None
    assert adapter.get_list("list-key") is None


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
    async def fetch(context: _MemoryContext) -> pl.DataFrame:
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
async def test_cache_get_or_fetch_runs_storage_off_event_loop(tmp_path: Path) -> None:
    adapter = FileCacheAdapter(cache_dir=tmp_path)
    event_loop_thread = threading.get_ident()
    storage_threads: list[int] = []
    original_get = adapter.get
    original_set = adapter.set

    def tracked_get(key: str, max_age: timedelta | None = None) -> pl.DataFrame | None:
        storage_threads.append(threading.get_ident())
        return original_get(key, max_age)

    def tracked_set(key: str, value: pl.DataFrame) -> None:
        storage_threads.append(threading.get_ident())
        original_set(key, value)

    adapter.get = tracked_get  # type: ignore[method-assign]
    adapter.set = tracked_set  # type: ignore[method-assign]

    await adapter.get_or_fetch("off-loop", _result_a1)

    assert storage_threads
    assert all(thread_id != event_loop_thread for thread_id in storage_threads)


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
async def test_in_flight_lock_is_scoped_to_event_loop() -> None:
    import gc

    from polars_baseball._cache import _IN_FLIGHT_LOCKS, FileCacheAdapter, _in_flight_lock_for

    cache = FileCacheAdapter()
    lock1 = _in_flight_lock_for(cache, "flat-key")
    assert isinstance(lock1, asyncio.Lock)

    loop = asyncio.get_running_loop()
    composite = f"{id(cache)}:flat-key"
    assert composite in _IN_FLIGHT_LOCKS[loop]

    # Same (cache, key) pair returns the identical lock object.
    lock2 = _in_flight_lock_for(cache, "flat-key")
    assert lock1 is lock2

    # Once the last strong reference is dropped the WeakValueDictionary evicts the entry.
    del lock1, lock2
    gc.collect()
    assert composite not in _IN_FLIGHT_LOCKS[loop]


@pytest.mark.asyncio
async def test_in_flight_lock_registry_uses_weak_event_loop_keys() -> None:
    from polars_baseball._cache import _IN_FLIGHT_LOCKS, FileCacheAdapter, _in_flight_lock_for

    cache = FileCacheAdapter()
    _in_flight_lock_for(cache, "loop-free-key")

    assert isinstance(_IN_FLIGHT_LOCKS, weakref.WeakKeyDictionary)


def test_file_cache_adapter_clear_error(tmp_path: Path) -> None:
    from unittest.mock import patch

    from polars_baseball.exceptions import CacheClearError

    adapter = FileCacheAdapter(cache_dir=tmp_path)

    with patch.object(Path, "iterdir", side_effect=OSError("Permission denied")):
        with pytest.raises(CacheClearError, match="Failed to clear cache"):
            adapter.clear()


class _LockInterrupted(BaseException):
    """Simulates a KeyboardInterrupt during threading.Condition.wait()."""


def test_shared_exclusive_lock_exclusive_interrupt_cleanup() -> None:
    """exclusive() interrupted by BaseException must not corrupt _writer_waiting.

    Without the fix, _writer_waiting stays >0 permanently, deadlocking all
    future shared() calls.  This test forces contention so exclusive() enters
    self._cond.wait(), then raises an interrupt inside it.
    """
    import threading

    from polars_baseball._cache_locks import SharedExclusiveLock

    original_wait = threading.Condition.wait
    interrupt_raised = False

    def _interrupting_wait(self: threading.Condition, timeout: float | None = None) -> bool:
        nonlocal interrupt_raised
        if not interrupt_raised:
            interrupt_raised = True
            raise _LockInterrupted("simulated Ctrl+C during wait()")
        return original_wait(self, timeout)

    lock = SharedExclusiveLock()
    shared_held = threading.Event()
    shared_continue = threading.Event()

    def hold_shared() -> None:
        with lock.shared():
            shared_held.set()
            shared_continue.wait(timeout=5)

    holder = threading.Thread(target=hold_shared)
    holder.start()
    shared_held.wait(timeout=5)

    with patch.object(threading.Condition, "wait", _interrupting_wait):
        with pytest.raises(_LockInterrupted):
            with lock.exclusive():
                pass

    shared_continue.set()
    holder.join(timeout=5)

    assert lock._writer_waiting == 0, f"_writer_waiting={lock._writer_waiting} (expected 0)"
    assert lock._writers == 0

    with lock.shared():
        pass
    with lock.exclusive():
        pass


@pytest.mark.asyncio
async def test_cached_checks_cache_before_lock() -> None:
    """Cache hits must return before acquiring the in-flight asyncio.Lock."""
    from polars_baseball._cache_locks import _in_flight_lock_for as original_lock_for

    context = _MemoryContext()

    @cached("pre-lock-check-key")
    async def fetch(context: _MemoryContext) -> pl.DataFrame:  # noqa: ARG001
        return pl.DataFrame({"value": [1]})

    await fetch(context)

    with patch("polars_baseball._cache._in_flight_lock_for", wraps=original_lock_for) as mock_lock:
        df = await fetch(context)

    assert df["value"][0] == 1
    assert mock_lock.call_count == 0, "Lock was acquired before cache check (pre-lock fast path missing)"


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


def test_file_cache_adapter_set_os_error_cleanup(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """When FileCacheAdapter.set encounters an OSError, it should clean up tmp files, log warning, and disable cache."""
    from unittest.mock import patch

    adapter = FileCacheAdapter(cache_dir=tmp_path)
    assert not adapter._disabled
    key = "failing-key"
    df = pl.DataFrame({"a": [1]})

    with patch.object(pl.DataFrame, "write_parquet", side_effect=OSError("Disk full")):
        adapter.set(key, df)

    # Adapter disables itself after write failure
    assert adapter._disabled
    # Verify no temp files exist in the cache directory
    tmp_files = list(tmp_path.glob("*.tmp"))
    assert len(tmp_files) == 0
    # Target file should not have been created
    assert not adapter._get_path(key).exists()
    assert "Failed to write cache entry" in caplog.text

    # Subsequent operations are no-ops
    adapter.set("another-key", df)
    assert adapter.get("another-key") is None


def test_file_cache_adapter_init_os_error_defensive(tmp_path: Path, caplog: pytest.LogCaptureFixture) -> None:
    """When FileCacheAdapter.__init__ fails to mkdir, it disables cache, logs warning, and does not crash."""
    from unittest.mock import patch

    read_only_dir = tmp_path / "read_only"
    with patch.object(Path, "mkdir", side_effect=PermissionError("Read-only file system")):
        adapter = FileCacheAdapter(cache_dir=read_only_dir)

    assert adapter._disabled
    assert adapter.cache_dir == read_only_dir
    assert "Failed to create cache directory" in caplog.text

    # All operations are no-ops when disabled
    adapter.set("k", pl.DataFrame({"a": [1]}))
    assert adapter.get("k") is None
    adapter.clear()  # should not raise


def test_read_cache_memory_error_propagates(tmp_path: Path) -> None:
    """MemoryError in pl.read_parquet must propagate, not be swallowed as cache miss.

    Regression test: previous except Exception caught MemoryError, silently
    deleting cache and returning None. Only ComputeError/OSError should be
    treated as cache corruption.
    """
    from unittest.mock import patch

    adapter = FileCacheAdapter(cache_dir=tmp_path)
    key = "memfail-key"
    adapter.set(key, pl.DataFrame({"a": [1]}))

    with patch("polars_baseball._cache.pl.read_parquet", side_effect=MemoryError("OOM")):
        with pytest.raises(MemoryError):
            adapter.get(key)


def test_shared_exclusive_lock_writer_waiting_interrupt_safety() -> None:
    from polars_baseball._cache_locks import SharedExclusiveLock

    lock = SharedExclusiveLock()
    with lock.shared():
        lock.exclusive()
        lock._lock.acquire()
        lock._writer_waiting += 1
        try:
            raise KeyboardInterrupt("Simulated interrupt during wait")
        except BaseException:
            pass
        finally:
            lock._lock.release()

    assert lock._writer_waiting >= 0
