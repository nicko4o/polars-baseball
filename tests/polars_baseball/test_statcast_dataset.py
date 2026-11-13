"""Tests for the Statcast compiled dataset scan/sync APIs and partition storage gateway."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch

import polars as pl
import pytest

from polars_baseball._season import most_recent_season
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


def _dataset_root(cache_dir: Path | None) -> Path:
    assert cache_dir is not None
    return cache_dir / "compiled-datasets" / "statcast"


def _partition_file(cache_dir: Path | None, year: int) -> Path:
    assert cache_dir is not None
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
    pl.DataFrame({"game_date": ["2023-11-05"]}).write_parquet(_partition_file(client.cache.cache_dir, 2023))

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


@pytest.mark.asyncio
async def test_sync_statcast_in_season_incremental_sync(client: BaseballClient) -> None:
    current_year = most_recent_season()
    part_file = _partition_file(client.cache.cache_dir, current_year)
    part_file.parent.mkdir(parents=True)
    initial_df = pl.DataFrame({"game_date": [f"{current_year}-04-01"], "game_year": [current_year]})
    initial_df.write_parquet(part_file)

    new_data = pl.DataFrame(
        {"game_date": [f"{current_year}-03-31", f"{current_year}-04-02"], "game_year": [current_year, current_year]}
    )
    with patch(
        "polars_baseball.savant.SavantClient._run_statcast_parallel", new=AsyncMock(return_value=[new_data])
    ) as mock_fetch:
        paths = await client.savant.sync_statcast([current_year])

    # Should have triggered incremental fetch with 2-day lookback window
    mock_fetch.assert_awaited_once()
    date_ranges = mock_fetch.call_args[0][0]
    # Check that incremental start is 2 days prior to 04-01
    assert date_ranges[0][0] == date(current_year, 3, 30)
    merged_df = pl.read_parquet(paths[0])
    # Only dates present in new_data are replaced; existing 04-01 is preserved
    assert merged_df["game_date"].to_list() == [
        f"{current_year}-03-31",
        f"{current_year}-04-01",
        f"{current_year}-04-02",
    ]


@pytest.mark.asyncio
async def test_scan_statcast_with_max_age_refreshes_stale_partition(client: BaseballClient) -> None:
    import os
    import time

    part_file = _partition_file(client.cache.cache_dir, 2023)
    part_file.parent.mkdir(parents=True)
    _DARVISH_DF.write_parquet(part_file)

    # Set file mtime to 10 days ago
    old_mtime = time.time() - 86400 * 10
    os.utime(part_file, (old_mtime, old_mtime))

    updated_df = _DARVISH_DF.with_columns(pl.lit(99.9).alias("release_speed"))
    with patch(
        "polars_baseball.savant.SavantClient._run_statcast_parallel", new=AsyncMock(return_value=[updated_df])
    ) as mock_fetch:
        result = await client.savant.scan_statcast(
            seasons=[2023],
            auto_download=True,
            max_age=timedelta(days=1),
        )

    mock_fetch.assert_awaited_once()
    df = result.collect()
    assert df["release_speed"].to_list() == [99.9, 99.9]


@pytest.mark.asyncio
async def test_scan_statcast_force_update(client: BaseballClient) -> None:
    part_file = _partition_file(client.cache.cache_dir, 2023)
    part_file.parent.mkdir(parents=True)
    _DARVISH_DF.write_parquet(part_file)

    refetched = _DARVISH_DF.with_columns(pl.lit(100.0).alias("release_speed"))
    with patch(
        "polars_baseball.savant.SavantClient._run_statcast_parallel", new=AsyncMock(return_value=[refetched])
    ) as mock_fetch:
        result = await client.savant.scan_statcast(
            seasons=[2023],
            auto_download=True,
            force_update=True,
        )

    mock_fetch.assert_awaited_once()
    df = result.collect()
    assert df["release_speed"].to_list() == [100.0, 100.0]


@pytest.mark.asyncio
async def test_sync_statcast_incomplete_historical_season_catches_up(client: BaseballClient) -> None:
    part_file = _partition_file(client.cache.cache_dir, 2023)
    part_file.parent.mkdir(parents=True)
    initial_df = pl.DataFrame({"game_date": ["2023-04-01"], "game_year": [2023]})
    initial_df.write_parquet(part_file)

    catchup_df = pl.DataFrame({"game_date": ["2023-11-02"], "game_year": [2023]})
    with patch(
        "polars_baseball.savant.SavantClient._run_statcast_parallel", new=AsyncMock(return_value=[catchup_df])
    ) as mock_fetch:
        paths = await client.savant.sync_statcast([2023])

    # Incomplete historical season (< Nov 1) must trigger catchup incremental sync
    mock_fetch.assert_awaited_once()
    merged = pl.read_parquet(paths[0])
    assert "2023-11-02" in merged["game_date"].to_list()


@pytest.mark.asyncio
async def test_sync_statcast_incremental_aborts_on_corrupt_read_and_falls_back_to_full(client: BaseballClient) -> None:
    current_year = most_recent_season()
    part_file = _partition_file(client.cache.cache_dir, current_year)
    part_file.parent.mkdir(parents=True)
    initial_df = pl.DataFrame({"game_date": [f"{current_year}-04-01"], "game_year": [current_year]})
    initial_df.write_parquet(part_file)

    # When partition_max_date succeeds but read_partition fails (returns None)
    full_season_data = pl.DataFrame(
        {"game_date": [f"{current_year}-04-01", f"{current_year}-04-05"], "game_year": [current_year, current_year]}
    )
    with (
        patch.object(client.savant._dataset_gateway, "read_partition", return_value=None),
        patch(
            "polars_baseball.savant.SavantClient._run_statcast_parallel", new=AsyncMock(return_value=[full_season_data])
        ) as mock_fetch,
    ):
        _ = await client.savant.sync_statcast([current_year])

    # Incremental should have aborted and fallen back to full-season scrape starting from early season
    mock_fetch.assert_awaited_once()
    called_ranges = mock_fetch.call_args[0][0]
    from polars_baseball._season import statcast_date_range

    expected_start = next(
        statcast_date_range(date(current_year, 1, 1), date(current_year, 12, 31), step=7, verbose=False)
    )[0]
    assert called_ranges[0][0] == expected_start


def test_statcast_docstrings_reflect_defaults() -> None:
    from polars_baseball._savant._statcast import SavantStatcastMixin

    sc_doc = SavantStatcastMixin.statcast.__doc__ or ""
    sync_doc = SavantStatcastMixin.sync_statcast.__doc__ or ""

    assert "default DEFAULT_STATCAST_CONCURRENCY_LIMIT (3)" in sc_doc
    assert "single-day query" in sc_doc
    assert "default DEFAULT_STATCAST_CONCURRENCY_LIMIT (3)" in sync_doc


@pytest.mark.asyncio
async def test_sync_and_scan_october_completed_season_not_re_synced(client: BaseballClient) -> None:
    # 2024 World Series ended 2024-10-30 (before Nov 1)
    part_file = _partition_file(client.cache.cache_dir, 2024)
    part_file.parent.mkdir(parents=True)
    pl.DataFrame({"game_date": ["2024-10-30"], "game_year": [2024]}).write_parquet(part_file)

    with patch(
        "polars_baseball.savant.SavantClient._run_statcast_parallel", new=AsyncMock(return_value=[_DARVISH_2024_DF])
    ) as mock_fetch:
        for _ in range(3):
            await client.savant.sync_statcast([2024])
            lf = await client.savant.scan_statcast(seasons=[2024], auto_download=True)
            assert lf.collect().height == 1

    mock_fetch.assert_not_awaited()


@pytest.mark.asyncio
async def test_sync_statcast_incremental_replaces_only_covered_dates_and_preserves_nulls(
    client: BaseballClient,
) -> None:
    current_year = most_recent_season()
    part_file = _partition_file(client.cache.cache_dir, current_year)
    part_file.parent.mkdir(parents=True)
    initial_df = pl.DataFrame(
        {
            "game_date": [None, f"{current_year}-03-31", f"{current_year}-04-01"],
            "release_speed": [90.0, 91.0, 92.0],
            "game_year": [current_year, current_year, current_year],
        }
    )
    initial_df.write_parquet(part_file)

    # New data only covers 04-01 (updated speed) and 04-02; 03-31 is empty in new fetch
    new_data = pl.DataFrame(
        {
            "game_date": [f"{current_year}-04-01", f"{current_year}-04-02"],
            "release_speed": [99.0, 95.0],
            "game_year": [current_year, current_year],
        }
    )
    with patch("polars_baseball.savant.SavantClient._run_statcast_parallel", new=AsyncMock(return_value=[new_data])):
        paths = await client.savant.sync_statcast([current_year])

    merged = pl.read_parquet(paths[0])
    # Null row and uncovered 03-31 are preserved; 04-01 is replaced by 99.0; 04-02 is added
    assert merged["game_date"].to_list() == [
        None,
        f"{current_year}-03-31",
        f"{current_year}-04-01",
        f"{current_year}-04-02",
    ]
    assert merged["release_speed"].to_list() == [90.0, 91.0, 99.0, 95.0]


@pytest.mark.asyncio
async def test_sync_statcast_self_heals_early_ending_historical_season(client: BaseballClient) -> None:
    # Suppose 2024 partition ends early at 2024-10-20 (< 2024-10-30 threshold)
    part_file = _partition_file(client.cache.cache_dir, 2024)
    part_file.parent.mkdir(parents=True)
    pl.DataFrame({"game_date": ["2024-10-20"], "game_year": [2024]}).write_parquet(part_file)

    # First catchup returns empty (no more games after 10-20) -> self-heals by marking complete
    with patch("polars_baseball.savant.SavantClient._run_statcast_parallel", new=AsyncMock(return_value=[])) as mock_1:
        await client.savant.sync_statcast([2024])
    mock_1.assert_awaited_once()
    assert client.savant._dataset_gateway.is_season_marked_complete(2024)

    # Subsequent syncs and auto_download scans must perform 0 requests
    with patch("polars_baseball.savant.SavantClient._run_statcast_parallel", new=AsyncMock(return_value=[])) as mock_2:
        for _ in range(3):
            await client.savant.sync_statcast([2024])
            lf = await client.savant.scan_statcast(seasons=[2024], auto_download=True)
            assert lf.collect().height == 1
    mock_2.assert_not_awaited()
