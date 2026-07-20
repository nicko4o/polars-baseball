from __future__ import annotations

import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import ClassVar

from polars_baseball._cache import CacheAdapter, FileCacheAdapter, global_cache
from polars_baseball._client import HttpClient


@dataclass
class BaseballContext:
    """Context container for HTTP client and caching adapter.

    Supports the async context manager protocol to ensure that resources (e.g., HTTP sessions)
    are cleaned up automatically upon exit.

    Use :meth:`BaseballContext.default` to get a lazily-initialized shared instance,
    or create your own with the ``async with`` pattern for explicit lifecycle control.

    Warning:
        If you pass a shared HttpClient instance to multiple BaseballContexts, exiting one context
        will close the shared HTTP client, affecting other contexts. In such cases, manage client
        lifecycles manually instead of using context managers.
    """

    http: HttpClient = field(default_factory=HttpClient)
    cache: CacheAdapter = field(default_factory=lambda: global_cache)
    github_token: str | None = None

    _default_instance: ClassVar[BaseballContext | None] = None
    _lock: ClassVar[threading.Lock] = threading.Lock()

    @classmethod
    def default(cls) -> BaseballContext:
        with cls._lock:
            if cls._default_instance is None:
                cls._default_instance = cls()
            return cls._default_instance

    @classmethod
    def reset_default(cls) -> None:
        with cls._lock:
            cls._default_instance = None

    @classmethod
    def with_file_cache(cls, cache_dir: Path, *, http: HttpClient | None = None) -> BaseballContext:
        return cls(http=http or HttpClient(), cache=FileCacheAdapter(cache_dir))

    async def __aenter__(self) -> BaseballContext:
        return self

    async def __aexit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc_val: BaseException | None,
        _exc_tb: object | None,
    ) -> None:
        await self.close()

    async def close(self) -> None:
        """Close HTTP resources owned by this context and reset the default if this is it."""
        with BaseballContext._lock:
            if BaseballContext._default_instance is self:
                BaseballContext._default_instance = None
        await self.http.close()


async def cleanup(ctx: BaseballContext | None = None) -> None:
    """Close HTTP resources and reset the default context singleton if applicable.

    When called without arguments, the current default singleton is targeted and
    cleared before closing, so no other caller can observe a half-closed client.

    Args:
        ctx: Context to clean up. If ``None``, the current default singleton is
             targeted. Passing an explicit context cleans it up and clears the
             default reference if it is the singleton.
    """
    if ctx is None:
        with BaseballContext._lock:
            target = BaseballContext._default_instance
            BaseballContext._default_instance = None
    else:
        target = ctx
        with BaseballContext._lock:
            if BaseballContext._default_instance is target:
                BaseballContext._default_instance = None
    if target is not None:
        await target.http.close()
