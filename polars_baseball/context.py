from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

from polars_baseball._cache import CacheAdapter, FileCacheAdapter, NullCacheAdapter, global_cache
from polars_baseball._client import HttpClient


@dataclass
class BaseballClient:
    """Explicit client instance managing transport sessions and isolated cache."""

    http: HttpClient = field(default_factory=HttpClient)
    cache: CacheAdapter = field(default_factory=lambda: global_cache)
    github_token: str | None = None

    @classmethod
    def with_file_cache(cls, cache_dir: Path, *, http: HttpClient | None = None) -> BaseballClient:
        return cls(http=http or HttpClient(), cache=FileCacheAdapter(cache_dir))

    @classmethod
    def with_null_cache(cls, *, http: HttpClient | None = None) -> BaseballClient:
        return cls(http=http or HttpClient(), cache=NullCacheAdapter())

    @classmethod
    def default(cls) -> BaseballClient:
        """Create a fresh default client instance."""
        return cls()

    @classmethod
    def reset_default(cls) -> None:
        """No-op retained for API compatibility without global singleton state."""
        pass

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
        """Close HTTP resources owned by this client."""
        await self.http.close()


BaseballContext = BaseballClient


async def cleanup(ctx: BaseballClient | None = None) -> None:
    """Close HTTP resources owned by the given client.

    If ctx is None, no-op as there is no shared global singleton.
    """
    if ctx is not None:
        await ctx.close()
