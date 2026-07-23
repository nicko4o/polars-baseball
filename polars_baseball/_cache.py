import asyncio
import functools
import hashlib
import inspect
import json
import logging
import tempfile
import threading
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable, Mapping
from datetime import datetime, timedelta
from pathlib import Path
from typing import ParamSpec, Protocol, TypeVar, cast

import polars as pl
from polars.exceptions import ComputeError

from polars_baseball._config import DEFAULT_CACHE_DIR
from polars_baseball.exceptions import CacheClearError

logger = logging.getLogger(__name__)

P = ParamSpec("P")
R = TypeVar("R")

_IN_FLIGHT_LOCKS: dict[str, asyncio.Lock] = {}
_IN_FLIGHT_LOCKS_GUARD = threading.Lock()


def _in_flight_lock_for(cache: object, key: str) -> asyncio.Lock:
    composite_key = f"{id(cache)}:{key}"
    with _IN_FLIGHT_LOCKS_GUARD:
        lock = _IN_FLIGHT_LOCKS.get(composite_key)
        if lock is None:
            lock = asyncio.Lock()
            _IN_FLIGHT_LOCKS[composite_key] = lock
        return lock


class CacheContext(Protocol):
    cache: "CacheAdapter"


def generate_cache_key(
    url: str,
    params: Mapping[str, object] | None = None,
) -> str:
    serialized_params = ""
    if params:
        sorted_params = sorted((k, str(v)) for k, v in params.items())
        serialized_params = json.dumps(sorted_params)

    raw_str = f"{url}?{serialized_params}"
    return hashlib.md5(raw_str.encode("utf-8")).hexdigest()


class CacheAdapter(ABC):
    """Pluggable cache backend for storing and retrieving DataFrames."""

    @abstractmethod
    def get(self, key: str, max_age: timedelta | None = None) -> pl.DataFrame | None:
        """Retrieve a cached DataFrame by key."""

    @abstractmethod
    def set(self, key: str, value: pl.DataFrame) -> None:
        """Store a DataFrame under the given key."""

    @abstractmethod
    def clear(self) -> None:
        """Remove all cached entries."""

    async def get_or_fetch(
        self,
        key: str,
        fetcher: Callable[[], Awaitable[pl.DataFrame]],
        *,
        max_age: timedelta | None = None,
        force_update: bool = False,
    ) -> pl.DataFrame:
        if not force_update:
            cached = await asyncio.to_thread(self.get, key, max_age)
            if cached is not None:
                return cached
        async with _in_flight_lock_for(self, key):
            if not force_update:
                cached = await asyncio.to_thread(self.get, key, max_age)
                if cached is not None:
                    return cached
            df = await fetcher()
            await asyncio.to_thread(self.set, key, df)
            return df


def _write_cached_file(path: Path, value: pl.DataFrame) -> bool:
    tmp_path: Path | None = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(dir=path.parent, suffix=".tmp", delete=False) as tmp:
            tmp_path = Path(tmp.name)
        value.write_parquet(tmp_path)
        tmp_path.replace(path)
        return True
    except OSError:
        logger.exception("Failed to write cache entry to %s", path)
        if tmp_path is not None and tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
        return False
    except Exception:
        if tmp_path is not None and tmp_path.exists():
            tmp_path.unlink(missing_ok=True)
        raise


def _clear_cache_dir(cache_dir: Path) -> None:
    if not cache_dir.exists():
        return
    try:
        for f in list(cache_dir.iterdir()):
            if f.is_file():
                f.unlink(missing_ok=True)
    except OSError as e:
        logger.error("Error clearing cache directory files: %s", cache_dir, exc_info=True)
        raise CacheClearError(f"Failed to clear cache directory files at {cache_dir}: {e}") from e
    try:
        if cache_dir.exists() and next(cache_dir.iterdir(), None) is None:
            cache_dir.rmdir()
    except OSError as e:
        logger.error("Error removing cache directory: %s", cache_dir, exc_info=True)
        raise CacheClearError(f"Failed to remove cache directory {cache_dir}: {e}") from e


def _try_read_cached(path: Path, key: str, max_age: timedelta | None = None) -> pl.DataFrame | None:
    if not path.exists():
        return None
    if max_age is not None:
        try:
            mtime = datetime.fromtimestamp(path.stat().st_mtime)
            if datetime.now() - mtime > max_age:
                path.unlink(missing_ok=True)
                return None
        except OSError:
            logger.warning("Failed to check cache age for %s, treating as miss", key)
            return None
    try:
        return pl.read_parquet(path)
    except (ComputeError, OSError) as e:
        logger.warning("Cache file corrupt for %s, deleting and treating as miss: %s", key, e)
        path.unlink(missing_ok=True)
        return None


class FileCacheAdapter(CacheAdapter):
    """File-based cache backend that stores DataFrames as Parquet files.

    Thread-safe via per-key locks and a clear lock.
    """

    def __init__(self, cache_dir: Path | None = None) -> None:
        self.cache_dir = cache_dir or DEFAULT_CACHE_DIR
        self._disabled = False
        try:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.warning("Failed to create cache directory %s, cache disabled: %s", self.cache_dir, e)
            self._disabled = True
        self._key_locks: dict[str, threading.Lock] = {}
        self._meta_lock = threading.Lock()
        self._clear_lock = threading.Lock()

    def _get_path(self, key: str) -> Path:
        safe_key = "".join(c if c.isalnum() else "_" for c in key)
        return self.cache_dir / f"{safe_key}.parquet"

    def _lock_for(self, key: str) -> threading.Lock:
        with self._meta_lock:
            lock = self._key_locks.get(key)
            if lock is None:
                lock = threading.Lock()
                self._key_locks[key] = lock
            return lock

    def get(self, key: str, max_age: timedelta | None = None) -> pl.DataFrame | None:
        if self._disabled:
            return None
        with self._lock_for(key):
            return _try_read_cached(self._get_path(key), key, max_age)

    def set(self, key: str, value: pl.DataFrame) -> None:
        if self._disabled:
            return
        with self._lock_for(key):
            write_ok = _write_cached_file(self._get_path(key), value)
            if not write_ok:
                self._disabled = True

    def clear(self) -> None:
        if self._disabled:
            return
        with self._clear_lock:
            with self._meta_lock:
                key_locks = list(self._key_locks.values())
            for lock in key_locks:
                lock.acquire()
            try:
                _clear_cache_dir(self.cache_dir)
            finally:
                for lock in reversed(key_locks):
                    lock.release()


class NullCacheAdapter(CacheAdapter):
    """No-op cache backend."""

    def get(self, key: str, max_age: timedelta | None = None) -> pl.DataFrame | None:
        return None

    def set(self, key: str, value: pl.DataFrame) -> None:
        return None

    def clear(self) -> None:
        return None


class GlobalCache(CacheAdapter):
    """Thread-safe process-wide cache adapter with dynamic backend switching."""

    def __init__(self, cache_dir: Path | None = None, *, use_null_default: bool = False) -> None:
        if use_null_default and cache_dir is None:
            self._adapter: CacheAdapter = NullCacheAdapter()
        else:
            self._adapter = FileCacheAdapter(cache_dir if cache_dir is not None else DEFAULT_CACHE_DIR)
        self._lock = threading.Lock()

    @property
    def cache_dir(self) -> Path:
        with self._lock:
            if not isinstance(self._adapter, FileCacheAdapter):
                raise RuntimeError("Global cache is not configured with a file-backed cache directory.")
            return self._adapter.cache_dir

    def configure(self, cache_dir: Path) -> None:
        adapter = FileCacheAdapter(cache_dir)
        with self._lock:
            self._adapter = adapter

    def get(self, key: str, max_age: timedelta | None = None) -> pl.DataFrame | None:
        return self._adapter.get(key, max_age)

    def set(self, key: str, value: pl.DataFrame) -> None:
        self._adapter.set(key, value)

    def clear(self) -> None:
        self._adapter.clear()


global_cache = GlobalCache()


def configure_cache(cache_dir: Path) -> None:
    """Configure the process-wide file cache directory."""
    global_cache.configure(cache_dir)


def cached(
    key: str | Callable[..., str],
    max_age: timedelta | None = None,
) -> Callable[[Callable[P, Awaitable[pl.DataFrame]]], Callable[P, Awaitable[pl.DataFrame]]]:
    """Cache a single DataFrame result, keyed by decorated function arguments."""

    def decorator(fn: Callable[P, Awaitable[pl.DataFrame]]) -> Callable[P, Awaitable[pl.DataFrame]]:
        sig = inspect.signature(fn)

        @functools.wraps(fn)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> pl.DataFrame:
            bound = sig.bind_partial(*args, **kwargs)
            bound.apply_defaults()
            call_kw = bound.arguments

            cache_key = key if isinstance(key, str) else key(**call_kw)
            effective_max_age = cast(timedelta | None, call_kw.get("cache_max_age", max_age))
            force_update = bool(call_kw.get("force_update", False))

            ctx_arg = call_kw.get("context")
            if ctx_arg is not None and hasattr(ctx_arg, "cache"):
                cache = cast(CacheAdapter, ctx_arg.cache)
            else:
                import importlib

                BaseballContext = importlib.import_module("polars_baseball.context").BaseballContext
                cache = cast(CacheAdapter, BaseballContext.default().cache)

            if not force_update:
                cached_val = await asyncio.to_thread(cache.get, cache_key, max_age=effective_max_age)
                if cached_val is not None:
                    return cached_val

            async with _in_flight_lock_for(cache, cache_key):
                if not force_update:
                    cached_val = await asyncio.to_thread(cache.get, cache_key, max_age=effective_max_age)
                    if cached_val is not None:
                        return cached_val
                val = await fn(*args, **kwargs)
                await asyncio.to_thread(cache.set, cache_key, val)
                return val

        return wrapper

    return decorator
