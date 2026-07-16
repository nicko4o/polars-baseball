import functools
import hashlib
import inspect
import json
import logging
import tempfile
import threading
import weakref
from abc import ABC, abstractmethod
from collections.abc import Awaitable, Callable, Mapping
from datetime import datetime, timedelta
from pathlib import Path
from typing import ParamSpec, Protocol, TypeVar, cast

import polars as pl

from polars_baseball._cache_locks import (
    _IN_FLIGHT_LOCKS as _IN_FLIGHT_LOCKS,
)
from polars_baseball._cache_locks import (
    SharedExclusiveLock,
    _in_flight_lock_for,
)
from polars_baseball._config import DEFAULT_CACHE_DIR
from polars_baseball.exceptions import CacheClearError

logger = logging.getLogger(__name__)

P = ParamSpec("P")
R = TypeVar("R")
_CONTEXT_PARAM_NAMES = ("context", "ctx", "_ctx")


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


_CACHE_PARTITION_KEY = "__cache_partition__"
_default_context_resolver: Callable[[], CacheContext] | None = None


def _set_default_cache_context_resolver(resolver: Callable[[], CacheContext]) -> None:
    global _default_context_resolver
    _default_context_resolver = resolver


class CacheAdapter(ABC):
    @abstractmethod
    def get(self, key: str, max_age: timedelta | None = None) -> pl.DataFrame | None:
        pass

    @abstractmethod
    def set(self, key: str, value: pl.DataFrame) -> None:
        pass

    @abstractmethod
    def clear(self) -> None:
        pass

    async def get_or_fetch(
        self,
        key: str,
        fetcher: Callable[[], Awaitable[pl.DataFrame]],
        *,
        max_age: timedelta | None = None,
        force_update: bool = False,
    ) -> pl.DataFrame:
        if not force_update:
            cached = self.get(key, max_age=max_age)
            if cached is not None:
                return cached
        async with _in_flight_lock_for(self, key):
            if not force_update:
                cached = self.get(key, max_age=max_age)
                if cached is not None:
                    return cached
            df = await fetcher()
            self.set(key, df)
            return df

    def get_list(self, key: str, max_age: timedelta | None = None) -> list[pl.DataFrame] | None:
        df = self.get(key, max_age=max_age)
        if df is None:
            return None
        if _CACHE_PARTITION_KEY not in df.columns:
            return None
        if df.is_empty():
            return []
        parts = df.sort(_CACHE_PARTITION_KEY).partition_by(_CACHE_PARTITION_KEY, as_dict=False, maintain_order=True)
        return [p.drop(_CACHE_PARTITION_KEY) for p in parts]

    def set_list(self, key: str, dfs: list[pl.DataFrame]) -> None:
        if not dfs:
            self.set(key, pl.DataFrame({_CACHE_PARTITION_KEY: pl.Series([], dtype=pl.Int64)}))
            return
        tagged = [df.with_columns(pl.lit(i).alias(_CACHE_PARTITION_KEY)) for i, df in enumerate(dfs)]
        self.set(key, pl.concat(tagged))


class FileCacheAdapter(CacheAdapter):
    def __init__(self, cache_dir: Path | None = None) -> None:
        self.cache_dir = cache_dir or DEFAULT_CACHE_DIR
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._key_locks: weakref.WeakValueDictionary[str, threading.Lock] = weakref.WeakValueDictionary()
        self._meta_lock = threading.Lock()
        self._rw_lock = SharedExclusiveLock()

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
        with self._rw_lock.shared():
            with self._lock_for(key):
                path = self._get_path(key)
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
                except Exception as e:
                    logger.warning("Cache file corrupt for %s, deleting and treating as miss: %s", key, e)
                    path.unlink(missing_ok=True)
                    return None

    def set(self, key: str, value: pl.DataFrame) -> None:
        with self._rw_lock.shared():
            with self._lock_for(key):
                path = self._get_path(key)
                path.parent.mkdir(parents=True, exist_ok=True)
                with tempfile.NamedTemporaryFile(dir=path.parent, suffix=".tmp", delete=False) as tmp:
                    tmp_path = Path(tmp.name)
                try:
                    value.write_parquet(tmp_path)
                    tmp_path.replace(path)
                except Exception:
                    tmp_path.unlink(missing_ok=True)
                    raise

    def clear(self) -> None:
        with self._rw_lock.exclusive():
            if not self.cache_dir.exists():
                return
            try:
                for f in list(self.cache_dir.iterdir()):
                    if f.is_file():
                        f.unlink(missing_ok=True)
            except OSError as e:
                logger.error("Error clearing cache directory files: %s", self.cache_dir, exc_info=True)
                raise CacheClearError(f"Failed to clear cache directory files at {self.cache_dir}: {e}") from e

            try:
                if self.cache_dir.exists() and next(self.cache_dir.iterdir(), None) is None:
                    self.cache_dir.rmdir()
            except OSError as e:
                logger.error("Error removing cache directory: %s", self.cache_dir, exc_info=True)
                raise CacheClearError(f"Failed to remove cache directory {self.cache_dir}: {e}") from e


class GlobalCache(CacheAdapter):
    def __init__(self, cache_dir: Path | None = None) -> None:
        self._adapter = FileCacheAdapter(cache_dir)

    @property
    def cache_dir(self) -> Path:
        return self._adapter.cache_dir

    def configure(self, cache_dir: Path) -> None:
        self._adapter = FileCacheAdapter(cache_dir)

    def get(self, key: str, max_age: timedelta | None = None) -> pl.DataFrame | None:
        return self._adapter.get(key, max_age)

    def set(self, key: str, value: pl.DataFrame) -> None:
        self._adapter.set(key, value)

    def get_list(self, key: str, max_age: timedelta | None = None) -> list[pl.DataFrame] | None:
        return self._adapter.get_list(key, max_age=max_age)

    def set_list(self, key: str, dfs: list[pl.DataFrame]) -> None:
        self._adapter.set_list(key, dfs)

    def clear(self) -> None:
        self._adapter.clear()


global_cache = GlobalCache()


def configure_cache(cache_dir: Path) -> None:
    """Configure the process-wide file cache directory.

    Args:
        cache_dir: Directory where cache parquet files are read and written.
    """
    global_cache.configure(cache_dir)


def _get_context(fn: Callable[P, object], args: tuple[object, ...], kwargs: Mapping[str, object]) -> CacheContext:
    sig = inspect.signature(fn)
    bound = sig.bind_partial(*args, **kwargs)
    for param_name in _CONTEXT_PARAM_NAMES:
        ctx = bound.arguments.get(param_name)
        if ctx is None:
            continue
        if not hasattr(ctx, "cache"):
            raise TypeError(f"{param_name} must expose a cache attribute")
        return cast(CacheContext, ctx)
    if _default_context_resolver is None:
        raise RuntimeError("Default cache context resolver has not been configured.")
    return _default_context_resolver()


def _resolve_key(
    fn: Callable[P, object],
    key_fn: Callable[..., str] | str,
    args: tuple[object, ...],
    kwargs: Mapping[str, object],
) -> str:
    if isinstance(key_fn, str):
        return key_fn

    sig_fn = inspect.signature(fn)
    bound_fn = sig_fn.bind_partial(*args, **kwargs)
    bound_fn.apply_defaults()
    all_params = bound_fn.arguments

    sig_key = inspect.signature(key_fn)
    key_kwargs: dict[str, object] = {}
    for param_name, param in sig_key.parameters.items():
        if param.kind == param.VAR_KEYWORD:
            for k, v in all_params.items():
                if k not in _CONTEXT_PARAM_NAMES and k not in key_kwargs:
                    key_kwargs[k] = v
            continue
        if param_name in _CONTEXT_PARAM_NAMES:
            ctx_val = next((all_params[name] for name in _CONTEXT_PARAM_NAMES if name in all_params), None)
            if ctx_val is not None:
                key_kwargs[param_name] = ctx_val
            continue
        if param_name in all_params:
            key_kwargs[param_name] = all_params[param_name]

    try:
        bound_key = sig_key.bind(**key_kwargs)
        return key_fn(*bound_key.args, **bound_key.kwargs)
    except TypeError:
        return key_fn(*args, **kwargs)


def _resolve_max_age(
    fn: Callable[P, object],
    max_age_fn: timedelta | None | Callable[..., timedelta | None],
    args: tuple[object, ...],
    kwargs: Mapping[str, object],
) -> timedelta | None:
    if not callable(max_age_fn):
        return max_age_fn

    sig_fn = inspect.signature(fn)
    bound_fn = sig_fn.bind_partial(*args, **kwargs)
    bound_fn.apply_defaults()
    all_params = bound_fn.arguments

    sig_max_age = inspect.signature(max_age_fn)
    max_age_kwargs: dict[str, object] = {}
    for param_name, param in sig_max_age.parameters.items():
        if param.kind == param.VAR_KEYWORD:
            for k, v in all_params.items():
                if k not in _CONTEXT_PARAM_NAMES and k not in max_age_kwargs:
                    max_age_kwargs[k] = v
            continue
        if param_name in _CONTEXT_PARAM_NAMES:
            ctx_val = next((all_params[name] for name in _CONTEXT_PARAM_NAMES if name in all_params), None)
            if ctx_val is not None:
                max_age_kwargs[param_name] = ctx_val
            continue
        if param_name in all_params:
            max_age_kwargs[param_name] = all_params[param_name]

    try:
        bound_max_age = sig_max_age.bind(**max_age_kwargs)
        return max_age_fn(*bound_max_age.args, **bound_max_age.kwargs)
    except TypeError:
        return max_age_fn(*args, **kwargs)


def _cached_execute(
    fn: Callable[..., Awaitable[R]],
    args: tuple[object, ...],
    kwargs: dict[str, object],
    key: str | Callable[..., str],
    max_age: timedelta | None | Callable[..., timedelta | None],
    cache_get: Callable[[CacheAdapter, str, timedelta | None], R | None],
    cache_set: Callable[[CacheAdapter, str, R], None],
) -> Awaitable[R]:
    ctx = _get_context(fn, args, kwargs)
    resolved_key = _resolve_key(fn, key, args, kwargs)
    resolved_max_age = _resolve_max_age(fn, max_age, args, kwargs)

    sig = inspect.signature(fn)
    bound = sig.bind_partial(*args, **kwargs)
    bound.apply_defaults()
    force_update = bound.arguments.get("force_update", False)

    async def run() -> R:
        async with _in_flight_lock_for(ctx.cache, resolved_key):
            if not force_update:
                cached_val = cache_get(ctx.cache, resolved_key, resolved_max_age)
                if cached_val is not None:
                    return cached_val
            val = await fn(*args, **kwargs)
            cache_set(ctx.cache, resolved_key, val)
            return val

    return run()


def cached(
    key: str | Callable[..., str],
    max_age: timedelta | None | Callable[..., timedelta | None] = None,
) -> Callable[[Callable[P, Awaitable[pl.DataFrame]]], Callable[P, Awaitable[pl.DataFrame]]]:
    def decorator(fn: Callable[P, Awaitable[pl.DataFrame]]) -> Callable[P, Awaitable[pl.DataFrame]]:
        @functools.wraps(fn)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> pl.DataFrame:
            return await _cached_execute(
                fn,
                args,
                kwargs,
                key,
                max_age,
                lambda c, k, a: c.get(k, max_age=a),
                lambda c, k, v: c.set(k, v),
            )

        return wrapper

    return decorator


def cached_list(
    key: str | Callable[..., str],
    max_age: timedelta | None | Callable[..., timedelta | None] = None,
) -> Callable[[Callable[P, Awaitable[list[pl.DataFrame]]]], Callable[P, Awaitable[list[pl.DataFrame]]]]:
    def decorator(fn: Callable[P, Awaitable[list[pl.DataFrame]]]) -> Callable[P, Awaitable[list[pl.DataFrame]]]:
        @functools.wraps(fn)
        async def wrapper(*args: P.args, **kwargs: P.kwargs) -> list[pl.DataFrame]:
            return await _cached_execute(
                fn,
                args,
                kwargs,
                key,
                max_age,
                lambda c, k, a: c.get_list(k, max_age=a),
                lambda c, k, v: c.set_list(k, v),
            )

        return wrapper

    return decorator
