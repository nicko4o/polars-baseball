from __future__ import annotations

import logging
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar

from polars_baseball._cache import CacheAdapter, FileCacheAdapter, NullCacheAdapter, global_cache
from polars_baseball._client import HttpClient


@dataclass
class BaseballClient:
    """Explicit client instance managing transport sessions and isolated cache."""

    http: HttpClient = field(default_factory=HttpClient)
    cache: CacheAdapter = field(default_factory=lambda: global_cache)
    github_token: str | None = None

    _default_instance: ClassVar[BaseballClient | None] = None
    _lock: ClassVar[threading.Lock] = threading.Lock()

    @classmethod
    def with_file_cache(cls, cache_dir: Path, *, http: HttpClient | None = None) -> BaseballClient:
        return cls(http=http or HttpClient(), cache=FileCacheAdapter(cache_dir))

    @classmethod
    def with_null_cache(cls, *, http: HttpClient | None = None) -> BaseballClient:
        return cls(http=http or HttpClient(), cache=NullCacheAdapter())

    @classmethod
    def default(cls) -> BaseballClient:
        """Get or lazily initialize the shared thread-safe default client."""
        if cls._default_instance is not None:
            return cls._default_instance
        with cls._lock:
            if cls._default_instance is None:
                cls._default_instance = cls()
            return cls._default_instance

    @classmethod
    def reset_default(cls) -> None:
        """Reset the shared default client singleton."""
        with cls._lock:
            cls._default_instance = None

    async def __aenter__(self) -> BaseballClient:
        return self

    async def __aexit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc_val: BaseException | None,
        _exc_tb: object | None,
    ) -> None:
        try:
            await self.close()
        except Exception as close_exc:
            if _exc_val is not None:
                logging.getLogger("polars_baseball").warning(
                    "Error closing BaseballClient during exception cleanup: %s", close_exc
                )
            else:
                raise

    async def close(self) -> None:
        """Close HTTP resources owned by this client and clear default singleton if this is it."""
        with BaseballClient._lock:
            if BaseballClient._default_instance is self:
                BaseballClient._default_instance = None
        await self.http.close()


BaseballContext = BaseballClient


async def cleanup(ctx: BaseballClient | None = None) -> None:
    """Close HTTP resources owned by the given client or the shared default singleton."""
    if ctx is None:
        with BaseballClient._lock:
            target = BaseballClient._default_instance
            BaseballClient._default_instance = None
    else:
        target = ctx
        with BaseballClient._lock:
            if BaseballClient._default_instance is target:
                BaseballClient._default_instance = None
    if target is not None:
        await target.close()
