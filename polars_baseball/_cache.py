from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import threading
import time
import weakref
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable, Mapping
from datetime import timedelta
from pathlib import Path
from typing import TypeVar

import polars as pl
from polars.exceptions import ComputeError

from polars_baseball._concurrency import LoopBoundLockRegistry
from polars_baseball._config import CACHE_SCHEMA_VERSION, DEFAULT_CACHE_DIR
from polars_baseball._storage_primitives import atomic_write_bytes, atomic_write_parquet
from polars_baseball.exceptions import CacheClearError

logger = logging.getLogger(__name__)

_T = TypeVar("_T")
_IN_FLIGHT_REGISTRY = LoopBoundLockRegistry()


def _in_flight_lock_for(cache: object, key: str) -> asyncio.Lock:
    return _IN_FLIGHT_REGISTRY.get_lock(f"{id(cache)}:{key}")


def generate_cache_key(
    url: str,
    params: Mapping[str, object] | None = None,
) -> str:
    serialized_params = ""
    if params:
        sorted_params = sorted((k, str(v)) for k, v in params.items())
        serialized_params = json.dumps(sorted_params)

    raw_str = f"{CACHE_SCHEMA_VERSION}:{url}?{serialized_params}"
    return hashlib.md5(raw_str.encode("utf-8"), usedforsecurity=False).hexdigest()


class CacheAdapter(ABC):
    """Pluggable cache backend for storing and retrieving DataFrames and raw data."""

    @property
    def cache_dir(self) -> Path | None:
        """Directory path where cache files are stored, or None if not file-backed."""
        return None

    @abstractmethod
    def get(self, key: str, max_age: timedelta | None = None) -> pl.DataFrame | None:
        """Retrieve a cached DataFrame by key."""

    @abstractmethod
    def set(self, key: str, value: pl.DataFrame) -> None:
        """Store a DataFrame under the given key."""

    @abstractmethod
    def get_raw(self, key: str, max_age: timedelta | None = None) -> bytes | None:
        """Retrieve cached raw bytes by key."""

    @abstractmethod
    def set_raw(self, key: str, value: bytes | str) -> None:
        """Store raw bytes or string under the given key."""

    @abstractmethod
    def clear(self) -> None:
        """Remove all cached entries."""

    async def _get_or_fetch_generic(
        self,
        key: str,
        fetcher: Callable[[], Awaitable[_T]],
        getter: Callable[[str, timedelta | None], _T | None],
        setter: Callable[[str, _T], None],
        *,
        max_age: timedelta | None = None,
        force_update: bool = False,
    ) -> _T:
        if not force_update:
            cached = await asyncio.to_thread(getter, key, max_age)
            if cached is not None:
                return cached
        async with _in_flight_lock_for(self, key):
            if not force_update:
                cached = await asyncio.to_thread(getter, key, max_age)
                if cached is not None:
                    return cached
            val = await fetcher()
            await asyncio.to_thread(setter, key, val)
            return val

    async def get_or_fetch(
        self,
        key: str,
        fetcher: Callable[[], Awaitable[pl.DataFrame]],
        *,
        max_age: timedelta | None = None,
        force_update: bool = False,
    ) -> pl.DataFrame:
        return await self._get_or_fetch_generic(
            key, fetcher, self.get, self.set, max_age=max_age, force_update=force_update
        )

    async def get_or_fetch_raw(
        self,
        key: str,
        fetcher: Callable[[], Awaitable[bytes | str]],
        *,
        max_age: timedelta | None = None,
        force_update: bool = False,
    ) -> bytes:
        raw = await self._get_or_fetch_generic(
            key, fetcher, self.get_raw, self.set_raw, max_age=max_age, force_update=force_update
        )
        return raw.encode("utf-8") if isinstance(raw, str) else raw


def _write_cached_file(path: Path, value: pl.DataFrame) -> bool:
    try:
        atomic_write_parquet(path, value)
        return True
    except OSError as e:
        logger.warning("Failed to write cache entry to %s: %s", path, e)
        return False


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


def _is_cache_expired(path: Path, key: str, max_age: timedelta | None) -> bool:
    if max_age is None:
        return False
    try:
        mtime = path.stat().st_mtime
        return (time.time() - mtime) > max_age.total_seconds()
    except OSError:
        logger.warning("Failed to check cache age for %s, treating as miss", key)
        return True


def _try_read_cached_entry(
    path: Path,
    key: str,
    reader: Callable[[Path], _T],
    error_types: tuple[type[Exception], ...],
    max_age: timedelta | None = None,
) -> _T | None:
    if not path.exists():
        return None
    if _is_cache_expired(path, key, max_age):
        return None
    try:
        return reader(path)
    except error_types as e:
        logger.warning("Cache file corrupt for %s, deleting and treating as miss: %s", key, e)
        path.unlink(missing_ok=True)
        return None


def _try_read_cached(path: Path, key: str, max_age: timedelta | None = None) -> pl.DataFrame | None:
    return _try_read_cached_entry(path, key, pl.read_parquet, (ComputeError, OSError), max_age)


def _write_cached_raw_file(path: Path, value: bytes | str) -> bool:
    raw_bytes = value.encode("utf-8") if isinstance(value, str) else value
    try:
        atomic_write_bytes(path, raw_bytes)
        return True
    except OSError as e:
        logger.warning("Failed to write raw cache entry to %s: %s", path, e)
        return False


def _try_read_cached_raw(path: Path, key: str, max_age: timedelta | None = None) -> bytes | None:
    return _try_read_cached_entry(path, key, lambda p: p.read_bytes(), (OSError,), max_age)


class FileCacheAdapter(CacheAdapter):
    """File-based cache backend that stores DataFrames as Parquet files.

    Thread-safe: per-key locks serialize access to individual entries, and
    a clear lock additionally serializes writes and clear() against each other.
    """

    def __init__(self, cache_dir: Path | None = None) -> None:
        self._cache_dir = cache_dir or DEFAULT_CACHE_DIR
        self._disabled = False
        try:
            self._cache_dir.mkdir(parents=True, exist_ok=True)
        except OSError as e:
            logger.warning("Failed to create cache directory %s, cache disabled: %s", self._cache_dir, e)
            self._disabled = True
        self._key_locks: weakref.WeakValueDictionary[str, threading.Lock] = weakref.WeakValueDictionary()
        self._meta_lock = threading.Lock()
        self._clear_lock = threading.Lock()

    @property
    def cache_dir(self) -> Path:
        return self._cache_dir

    def _get_path(self, key: str) -> Path:
        safe_key = "".join(c if c.isalnum() else "_" for c in key)
        return self._cache_dir / f"{safe_key}.parquet"

    def _get_raw_path(self, key: str) -> Path:
        safe_key = "".join(c if c.isalnum() else "_" for c in key)
        return self._cache_dir / f"{safe_key}.raw"

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
        return _try_read_cached(self._get_path(key), key, max_age)

    def set(self, key: str, value: pl.DataFrame) -> None:
        if self._disabled:
            return
        with self._clear_lock, self._lock_for(key):
            _write_cached_file(self._get_path(key), value)

    def get_raw(self, key: str, max_age: timedelta | None = None) -> bytes | None:
        if self._disabled:
            return None
        return _try_read_cached_raw(self._get_raw_path(key), key, max_age)

    def set_raw(self, key: str, value: bytes | str) -> None:
        if self._disabled:
            return
        with self._clear_lock, self._lock_for(key):
            _write_cached_raw_file(self._get_raw_path(key), value)

    def clear(self) -> None:
        if self._disabled:
            return
        with self._clear_lock:
            _clear_cache_dir(self._cache_dir)
            with self._meta_lock:
                self._key_locks.clear()


class NullCacheAdapter(CacheAdapter):
    """No-op cache backend."""

    def get(self, key: str, max_age: timedelta | None = None) -> pl.DataFrame | None:
        return None

    def set(self, key: str, value: pl.DataFrame) -> None:
        return None

    def get_raw(self, key: str, max_age: timedelta | None = None) -> bytes | None:
        return None

    def set_raw(self, key: str, value: bytes | str) -> None:
        return None

    def clear(self) -> None:
        return None
