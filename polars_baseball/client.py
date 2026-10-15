from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

from polars_baseball._cache import CacheAdapter, FileCacheAdapter, NullCacheAdapter
from polars_baseball._client import HttpClient
from polars_baseball._config import _resolve_default_cache_dir

if TYPE_CHECKING:
    from polars_baseball.bref import BRefClient
    from polars_baseball.fangraphs import FanGraphsClient
    from polars_baseball.lahman import LahmanClient
    from polars_baseball.lookup import LookupClient
    from polars_baseball.mlb import MlbClient
    from polars_baseball.retrosheet import RetrosheetClient
    from polars_baseball.savant import SavantClient

logger = logging.getLogger("polars_baseball")


class BaseballClient:
    """Explicit client instance managing transport sessions, cache, and provider namespaces."""

    def __init__(
        self,
        *,
        http: HttpClient | None = None,
        cache: CacheAdapter | None = None,
        cache_dir: Path | None = None,
        github_token: str | None = None,
    ) -> None:
        self.http: HttpClient = http or HttpClient()
        if cache is not None:
            self.cache: CacheAdapter = cache
        elif cache_dir is not None:
            self.cache = FileCacheAdapter(cache_dir)
        else:
            self.cache = FileCacheAdapter(_resolve_default_cache_dir())
        self.github_token: str | None = github_token

        from polars_baseball.bref import BRefClient
        from polars_baseball.fangraphs import FanGraphsClient
        from polars_baseball.lahman import LahmanClient
        from polars_baseball.lookup import LookupClient
        from polars_baseball.mlb import MlbClient
        from polars_baseball.retrosheet import RetrosheetClient
        from polars_baseball.savant import SavantClient

        self.savant: SavantClient = SavantClient(self)
        self.mlb: MlbClient = MlbClient(self)
        self.bref: BRefClient = BRefClient(self)
        self.fangraphs: FanGraphsClient = FanGraphsClient(self)
        self.retrosheet: RetrosheetClient = RetrosheetClient(self)
        self.lahman: LahmanClient = LahmanClient(self)
        self.lookup: LookupClient = LookupClient(self)

    @classmethod
    def with_file_cache(cls, cache_dir: Path, *, http: HttpClient | None = None) -> BaseballClient:
        return cls(http=http or HttpClient(), cache=FileCacheAdapter(cache_dir))

    @classmethod
    def with_null_cache(cls, *, http: HttpClient | None = None) -> BaseballClient:
        return cls(http=http or HttpClient(), cache=NullCacheAdapter())

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
                logger.warning("Error closing BaseballClient during exception cleanup: %s", close_exc)
            else:
                raise

    async def close(self) -> None:
        """Close underlying HTTP transport sessions."""
        await self.http.close()

    aclose = close


# Transitional alias for smooth internal refactoring
BaseballContext = BaseballClient
