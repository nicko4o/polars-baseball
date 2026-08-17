"""Public async API for the local Statcast compiled dataset (scan + sync)."""

from collections.abc import Sequence
from datetime import date
from pathlib import Path

import polars as pl

from polars_baseball._config import DEFAULT_STATCAST_CONCURRENCY_LIMIT, STATCAST_DATE_STEP, STATCAST_FIRST_YEAR
from polars_baseball._season import most_recent_season, statcast_date_range
from polars_baseball.apis.statcast import _align_schemas, _run_statcast_parallel
from polars_baseball.context import BaseballContext
from polars_baseball.exceptions import InvalidParameterError, UpstreamUnavailableError
from polars_baseball.gateways.statcast_dataset import StatcastDatasetGateway

_YEAR_END_MONTH = 12
_YEAR_END_DAY = 31


def _normalize_seasons(seasons: int | Sequence[int] | None) -> list[int] | None:
    if seasons is None:
        return None
    if isinstance(seasons, int):
        return [seasons]
    return list(seasons)


def _validate_season(year: int) -> None:
    max_year = most_recent_season()
    if year < STATCAST_FIRST_YEAR or year > max_year:
        raise InvalidParameterError(
            f"Season {year} is out of range; Statcast data is available for {STATCAST_FIRST_YEAR}-{max_year}."
        )


async def sync_statcast(
    seasons: int | Sequence[int],
    *,
    force_update: bool = False,
    verbose: bool = True,
    concurrency_limit: int = DEFAULT_STATCAST_CONCURRENCY_LIMIT,
    context: BaseballContext | None = None,
) -> list[Path]:
    """Scrape and persist full-season Statcast partitions to the local compiled dataset.

    Fetches pitch-level data via the Savant Gateway in ~7-day chunks and writes
    one Hive partition per season at
    ``{cache_dir}/compiled-datasets/statcast/year={year}/statcast.parquet``.

    Note:
        - Existing partitions are reused unless ``force_update`` is True.
        - Requires a file-backed cache directory.
    """
    years = _normalize_seasons(seasons)
    if years is None or not years:
        raise InvalidParameterError("sync_statcast requires at least one season.")

    ctx = context or BaseballContext.default()
    gateway = StatcastDatasetGateway(ctx)

    paths: list[Path] = []
    for year in years:
        _validate_season(year)
        if gateway.year_exists(year) and not force_update:
            paths.append(gateway.partition_path(year))
            continue
        df = await _fetch_season(year, ctx, verbose, concurrency_limit)
        paths.append(await gateway.write_partition(year, df))
    return paths


async def scan_statcast(
    seasons: int | Sequence[int] | None = None,
    *,
    auto_download: bool = False,
    context: BaseballContext | None = None,
) -> pl.LazyFrame:
    """Lazily scan the local Statcast Hive-partitioned Parquet dataset.

    Returns a ``polars.LazyFrame`` with full predicate and projection pushdown.
    When ``seasons`` is None, all locally synced partitions are scanned.

    Note:
        - Missing seasons raise ``UpstreamUnavailableError`` unless
          ``auto_download`` is True, in which case they are synced first.
        - Requires a file-backed cache directory.
    """
    ctx = context or BaseballContext.default()
    gateway = StatcastDatasetGateway(ctx)

    years = _normalize_seasons(seasons)
    if years is not None:
        for year in years:
            _validate_season(year)
        synced = set(gateway.synced_seasons())
        missing = [year for year in years if year not in synced]
        if missing:
            if auto_download:
                await sync_statcast(missing, context=ctx)
            else:
                raise UpstreamUnavailableError(
                    f"No local Statcast partition for season(s): {sorted(missing)}. "
                    "Run sync_statcast() or pass auto_download=True."
                )
    return gateway.scan(years)


async def _fetch_season(
    year: int,
    ctx: BaseballContext,
    verbose: bool,
    concurrency_limit: int,
) -> pl.DataFrame:
    start = date(year, 1, 1)
    stop = date(year, _YEAR_END_MONTH, _YEAR_END_DAY)
    date_range = list(statcast_date_range(start, stop, step=STATCAST_DATE_STEP, verbose=False))
    frames = await _run_statcast_parallel(date_range, None, verbose, ctx, concurrency_limit)
    dfs = [df for df in frames if df is not None and not df.is_empty()]
    if not dfs:
        return pl.DataFrame()
    return pl.concat(_align_schemas(dfs), how="diagonal")
