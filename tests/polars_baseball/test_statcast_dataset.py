"""Tests for the Statcast compiled dataset scan/sync APIs and partition storage gateway."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

import polars as pl
import pytest

from polars_baseball.client import BaseballClient
from polars_baseball.exceptions import InvalidParameterError, UpstreamUnavailableError

_DARVISH_DF = pl.DataFrame(
    {
        "pitch_type": ["FF", "SL"],
        "game_date": ["2023-04-01", "2023-04-01"],
        "player_name": ["Yu Darvish"] * 2,
        "batter": [608380, 592450],
        "pitcher": [506433, 506433],
        "zone": [5, 9],
        "game_year": [2023, 2023],
        "release_speed": [95.1, 87.2],
    }
)

_DARVISH_2024_DF = _DARVISH_DF.with_columns(
    pl.lit("2024-04-01").cast(pl.String).alias("game_date"),
    pl.lit(2024).cast(pl.Int64).alias("game_year"),
)


def _dataset_root(cache_dir: Path) -> Path:
    return cache_dir / "compiled-datasets" / "statcast"


def _partition_file(cache_dir: Path, year: int) -> Path:
    return _dataset_root(cache_dir) / f"year={year}" / "statcast.parquet"


@pytest.fixture
def client(tmp_path: Path) -> BaseballClient:
    return BaseballClient.with_file_cache(tmp_path)


@pytest.mark.asyncio
async def test_scan_statcast_returns_empty_lazyframe_when_no_partitions(client: BaseballClient) -> None:
    result = await client.savant.scan_statcast()
    assert isinstance(result, pl.LazyFrame)
    assert result.collect().is_empty()


@pytest.mark.asyncio
async def test_sync_statcast_writes_hive_partition(client: BaseballClient) -> None:
    with patch("polars_baseball.savant.SavantClient._run_statcast_parallel", new=AsyncMock(return_value=[_DARVISH_DF])):
        paths = await client.savant.sync_statcast([2023])

    assert len(paths) == 1
    expected = _partition_file(client.cache.cache_dir, 2023)
    assert paths[0] == expected
    assert expected.exists()

    df = pl.scan_parquet([expected], hive_partitioning=True).collect()
    assert df.height == 2
    assert df["year"][0] == 2023


@pytest.mark.asyncio
async def test_sync_statcast_skips_existing_partition_without_force(client: BaseballClient) -> None:
    _partition_file(client.cache.cache_dir, 2023).parent.mkdir(parents=True)
    pl.DataFrame({"game_date": ["2023-04-01"]}).write_parquet(_partition_file(client.cache.cache_dir, 2023))

    with patch(
        "polars_baseball.savant.SavantClient._run_statcast_parallel", new=AsyncMock(return_value=[_DARVISH_DF])
    ) as mock_fetch:
        paths = await client.savant.sync_statcast([2023])

    mock_fetch.assert_not_awaited()
    assert len(paths) == 1


@pytest.mark.asyncio
async def test_sync_statcast_force_update_refetches_and_overwrites(client: BaseballClient) -> None:
    stale = pl.DataFrame({"game_date": ["2023-04-01"], "game_year": [2023]})
    _partition_file(client.cache.cache_dir, 2023).parent.mkdir(parents=True)
    stale.write_parquet(_partition_file(client.cache.cache_dir, 2023))

    with patch(
        "polars_baseball.savant.SavantClient._run_statcast_parallel", new=AsyncMock(return_value=[_DARVISH_DF])
    ) as mock_fetch:
        paths = await client.savant.sync_statcast([2023], force_update=True)

    mock_fetch.assert_awaited_once()
    df = pl.read_parquet(paths[0])
    assert df.height == 2


@pytest.mark.asyncio
async def test_sync_statcast_validates_season_range(client: BaseballClient) -> None:
    with patch("polars_baseball.savant.SavantClient._run_statcast_parallel", new=AsyncMock(return_value=[_DARVISH_DF])):
        with pytest.raises(InvalidParameterError):
            await client.savant.sync_statcast([1999])


@pytest.mark.asyncio
async def test_scan_statcast_filters_by_season_with_hive_year_column(client: BaseballClient) -> None:
    for year, frame in ((2023, _DARVISH_DF), (2024, _DARVISH_2024_DF)):
        _partition_file(client.cache.cache_dir, year).parent.mkdir(parents=True)
        frame.write_parquet(_partition_file(client.cache.cache_dir, year))

    result = await client.savant.scan_statcast(seasons=[2024])
    df = result.collect()

    assert "year" in df.columns
    assert df["year"].to_list() == [2024, 2024]
    assert df["game_year"].to_list() == [2024, 2024]


@pytest.mark.asyncio
async def test_scan_statcast_scans_all_partitions_when_seasons_none(client: BaseballClient) -> None:
    for year, frame in ((2023, _DARVISH_DF), (2024, _DARVISH_2024_DF)):
        _partition_file(client.cache.cache_dir, year).parent.mkdir(parents=True)
        frame.write_parquet(_partition_file(client.cache.cache_dir, year))

    result = await client.savant.scan_statcast()
    df = result.collect()
    assert set(df["year"].to_list()) == {2023, 2024}


@pytest.mark.asyncio
async def test_scan_statcast_raises_for_missing_season_without_auto_download(client: BaseballClient) -> None:
    with pytest.raises(UpstreamUnavailableError):
        await client.savant.scan_statcast(seasons=[2023])


@pytest.mark.asyncio
async def test_scan_statcast_auto_download_syncs_missing_season(client: BaseballClient) -> None:
    with patch("polars_baseball.savant.SavantClient._run_statcast_parallel", new=AsyncMock(return_value=[_DARVISH_DF])):
        result = await client.savant.scan_statcast(seasons=[2023], auto_download=True)

    df = result.collect()
    assert df.height == 2
    assert df["year"].to_list() == [2023, 2023]


@pytest.mark.asyncio
async def test_write_partition_normalizes_missing_canonical_columns(client: BaseballClient) -> None:
    sparse = pl.DataFrame({"pitcher": [506433], "game_date": ["2023-04-01"], "game_year": [2023]})

    with patch("polars_baseball.savant.SavantClient._run_statcast_parallel", new=AsyncMock(return_value=[sparse])):
        paths = await client.savant.sync_statcast([2023])

    df = pl.read_parquet(paths[0])
    assert df["pitch_type"].to_list() == [None]
    assert df["zone"].dtype == pl.Int64
    assert df["release_speed"].dtype == pl.Float64


@pytest.mark.asyncio
async def test_write_partition_casts_types_to_canonical_schema(client: BaseballClient) -> None:
    wrong_types = pl.DataFrame(
        {"game_date": ["2023-04-01"], "zone": ["5"], "release_speed": ["95.1"], "game_year": [2023]}
    )

    with patch("polars_baseball.savant.SavantClient._run_statcast_parallel", new=AsyncMock(return_value=[wrong_types])):
        paths = await client.savant.sync_statcast([2023])

    df = pl.read_parquet(paths[0])
    assert df["zone"].dtype == pl.Int64
    assert df["release_speed"].dtype == pl.Float64
