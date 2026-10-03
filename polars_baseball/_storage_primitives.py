"""Atomic storage primitives, cache path resolution, and concurrent file locks."""

from __future__ import annotations

import asyncio
import tempfile
import threading
import weakref
import zipfile
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING

import polars as pl

from polars_baseball.exceptions import UpstreamDataCorruptedError

if TYPE_CHECKING:
    from polars_baseball.context import BaseballContext

_LOCKS: weakref.WeakValueDictionary[str, asyncio.Lock] = weakref.WeakValueDictionary()
_LOCKS_GUARD = threading.Lock()


def resolve_cache_dir(context: BaseballContext) -> Path | None:
    """Extract cache_dir from context if file-backed."""
    return context.cache.cache_dir


def get_file_lock(key: str) -> asyncio.Lock:
    """Return an asyncio.Lock tied to the current event loop and key."""
    loop = asyncio.get_running_loop()
    lock_key = f"{id(loop)}:{key}"
    with _LOCKS_GUARD:
        lock = _LOCKS.get(lock_key)
        if lock is None:
            lock = asyncio.Lock()
            _LOCKS[lock_key] = lock
        return lock


def validate_safe_path_component(value: str) -> None:
    """Validate that a path component is relative and safe.

    Raises ValueError for absolute paths or path-traversal patterns.
    """
    path = Path(value)
    if not value or path.is_absolute() or ".." in path.parts:
        raise ValueError(f"Unsafe compiled dataset path: {value}")


def validate_zip_archive(path: Path) -> None:
    """Validate that a file is a readable ZIP archive.

    Raises UpstreamDataCorruptedError on bad or truncated ZIP files.
    """
    try:
        with zipfile.ZipFile(path):
            return None
    except (zipfile.BadZipFile, OSError) as err:
        raise UpstreamDataCorruptedError(f"Bad zip file: {path}") from err


def atomic_write_file(path: Path, write_func: Callable[[Path], object]) -> None:
    """Write data to a file atomically via temp-file-then-replace."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, suffix=".tmp", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        write_func(tmp_path)
        tmp_path.replace(path)
    except Exception:
        tmp_path.unlink(missing_ok=True)
        raise


def atomic_write_bytes(path: Path, raw: bytes) -> None:
    """Write bytes to a file atomically."""
    atomic_write_file(path, lambda p: p.write_bytes(raw))


def atomic_write_parquet(path: Path, df: pl.DataFrame) -> None:
    """Write a DataFrame to a parquet file atomically."""
    atomic_write_file(path, df.write_parquet)
