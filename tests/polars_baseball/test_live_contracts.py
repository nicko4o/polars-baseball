import polars as pl
import pytest

from polars_baseball import (
    standings,
    statcast_single_game,
)
from polars_baseball.apis.savant_leaderboards import statcast_batter_exitvelo_barrels
from tests._async_utils import run_async


@pytest.mark.live
def test_live_mlb_standings() -> None:
    # Fetch historical standings for 2023 season
    dfs = run_async(standings(season=2023))
    assert isinstance(dfs, list)
    assert len(dfs) > 0

    df = dfs[0]
    assert isinstance(df, pl.DataFrame)
    assert df.height > 0
    assert "Tm" in df.columns
    assert "W" in df.columns
    assert "L" in df.columns


@pytest.mark.live
def test_live_savant_statcast_single_game() -> None:
    # Fetch a single real game from 2024 (game_pk=747046)
    df = run_async(statcast_single_game(game_pk=747046))
    assert isinstance(df, pl.DataFrame)
    assert df.height > 0
    assert "pitch_type" in df.columns
    assert ("player_name" in df.columns) or ("last_name, first_name" in df.columns)


@pytest.mark.live
def test_live_savant_exit_velo_barrels() -> None:
    # Fetch batter exit velocity leaderboard for 2023 season
    df = run_async(statcast_batter_exitvelo_barrels(year=2023))
    assert isinstance(df, pl.DataFrame)
    assert df.height > 0
    assert ("player_name" in df.columns) or ("last_name, first_name" in df.columns)
    assert "player_id" in df.columns


@pytest.mark.live
def test_live_fangraphs_batting() -> None:
    from polars_baseball.apis.fangraphs import FanGraphsRequest, fg_data

    # Request batting stats for 2023 season with custom columns
    request = FanGraphsRequest.batting(start_season=2023, stat_columns=["WAR", "OPS"])
    df = run_async(fg_data(request))
    assert isinstance(df, pl.DataFrame)
    assert df.height > 0
    # Confirm contract: must contain standard columns + requested columns
    assert "Name" in df.columns
    assert "WAR" in df.columns
    assert "OPS" in df.columns
