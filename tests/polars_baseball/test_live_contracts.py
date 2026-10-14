import polars as pl
import pytest

from polars_baseball import (
    BaseballContext,
    mlb,
    savant,
)
from polars_baseball.apis.savant_leaderboards import statcast_exitvelo_barrels
from polars_baseball.exceptions import PolarsBaseballHttpError
from tests._async_utils import run_async


@pytest.mark.live
def test_live_mlb_standings() -> None:
    # Fetch historical standings for 2023 season
    async def run() -> pl.DataFrame:
        async with BaseballContext() as ctx:
            return await mlb.standings(season=2023, context=ctx)

    df = run_async(run())
    assert isinstance(df, pl.DataFrame)
    assert df.height > 0
    assert "Tm" in df.columns
    assert "W" in df.columns
    assert "L" in df.columns


@pytest.mark.live
def test_live_savant_statcast_single_game() -> None:
    # Fetch a single real game from 2024 (game_pk=747046)
    async def run() -> pl.DataFrame:
        async with BaseballContext() as ctx:
            lf = await savant.single_game(game_pk=747046, context=ctx)
            return lf.collect()

    df = run_async(run())
    assert isinstance(df, pl.DataFrame)
    assert df.height > 0
    assert "pitch_type" in df.columns
    assert ("player_name" in df.columns) or ("last_name, first_name" in df.columns)


@pytest.mark.live
def test_live_savant_exit_velo_barrels() -> None:
    # Fetch batter exit velocity leaderboard for 2023 season
    async def run() -> pl.DataFrame:
        async with BaseballContext() as ctx:
            return await statcast_exitvelo_barrels(year=2023, player_type="batter", context=ctx)

    df = run_async(run())
    assert isinstance(df, pl.DataFrame)
    assert df.height > 0
    assert ("player_name" in df.columns) or ("last_name, first_name" in df.columns)
    assert "player_id" in df.columns


@pytest.mark.live
def test_live_fangraphs_batting() -> None:
    import polars_baseball as pb

    async def run() -> pl.DataFrame:
        async with BaseballContext() as ctx:
            return await pb.fangraphs.batting(start_season=2023, stat_columns=["WAR", "OPS"], context=ctx)

    try:
        df = run_async(run())
    except PolarsBaseballHttpError as e:
        if e.status_code == 403 or "Cloudflare" in str(e):
            pytest.skip(f"FanGraphs live test skipped due to Cloudflare protection (HTTP 403): {e}")
        raise

    assert isinstance(df, pl.DataFrame)
    assert df.height > 0
    # Confirm contract: must contain standard columns + requested columns
    assert "Name" in df.columns
    assert "WAR" in df.columns
    assert "OPS" in df.columns


@pytest.mark.live
def test_live_statcast_benchmark_range_does_not_schema_error() -> None:
    # Benchmark date range from 2024 to verify alignment and guard against upstream schema drift
    async def run() -> pl.DataFrame:
        async with BaseballContext() as ctx:
            lf = await savant.statcast(
                start_date="2024-04-01",
                end_date="2024-04-02",
                verbose=False,
                context=ctx,
            )
            return lf.collect()

    df = run_async(run())
    assert isinstance(df, pl.DataFrame)
    assert df.height > 0
