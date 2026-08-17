"""Compiled dataset storage gateway for Hive-partitioned Statcast parquet datasets."""

import re
from pathlib import Path

import polars as pl

from polars_baseball._schemas.statcast import normalize_statcast_partition
from polars_baseball.context import BaseballContext
from polars_baseball.exceptions import UpstreamUnavailableError
from polars_baseball.gateways.compiled import (
    COMPILED_DATASETS_DIR,
    _cache_dir,
    _lock_for,
    _write_parquet_atomic,
)

_DATASET_DIR = "statcast"
_PARTITION_FILE = "statcast.parquet"
_YEAR_PARTITION_PATTERN = re.compile(r"^year=(\d{4})$")


class StatcastDatasetGateway:
    """File-backed Hive-partitioned storage for full-season Statcast data.

    Layout: ``{cache_dir}/compiled-datasets/statcast/year={year}/statcast.parquet``.
    Writes are atomic (temp file + replace) and guarded by per-path locks,
    reusing the CompiledDatasetGateway primitives.
    """

    def __init__(self, context: BaseballContext) -> None:
        self._context = context
        self._cache_dir = _cache_dir(context)

    def _root(self) -> Path:
        if self._cache_dir is None:
            raise UpstreamUnavailableError("Compiled dataset requires a file-backed cache directory.")
        return self._cache_dir / COMPILED_DATASETS_DIR / _DATASET_DIR

    def partition_path(self, year: int) -> Path:
        return self._root() / f"year={year}" / _PARTITION_FILE

    def year_exists(self, year: int) -> bool:
        return self.partition_path(year).exists()

    def synced_seasons(self) -> list[int]:
        root = self._root()
        if not root.exists():
            return []
        return [
            int(match.group(1))
            for entry in root.iterdir()
            if entry.is_dir() and (match := _YEAR_PARTITION_PATTERN.match(entry.name)) is not None
        ]

    async def write_partition(self, year: int, df: pl.DataFrame) -> Path:
        path = self.partition_path(year)
        normalized = normalize_statcast_partition(df)
        async with _lock_for(str(path)):
            await _write_partition_async(path, normalized)
        return path

    def scan(self, seasons: list[int] | None = None) -> pl.LazyFrame:
        root = self._root()
        if not root.exists():
            return pl.DataFrame().lazy()

        if seasons is None:
            seasons = self.synced_seasons()

        paths = [self.partition_path(year) for year in seasons]
        existing = [path for path in paths if path.exists()]
        if not existing:
            return pl.DataFrame().lazy()
        return pl.scan_parquet(existing, hive_partitioning=True, missing_columns="insert")


async def _write_partition_async(path: Path, df: pl.DataFrame) -> None:
    import asyncio

    await asyncio.to_thread(_write_parquet_atomic, path, df)
