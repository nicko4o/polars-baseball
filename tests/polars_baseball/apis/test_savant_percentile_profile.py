"""Tests for composite percentile ranks and player percentile profiles."""

from collections.abc import Callable
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import polars as pl
import pytest

from polars_baseball._client import HttpClient
from polars_baseball.apis.savant_leaderboards import (
    statcast_composite_percentile_ranks,
    statcast_player_percentile_profile,
)
from polars_baseball.context import BaseballContext


async def _mock_fetch(key: str, fetcher: Callable[[], Any], **kwargs: object) -> Any:
    return await fetcher()


_MOCK_PERCENTILES_BATTER = (
    "player_name,player_id,year,xwoba,xba,xslg,xiso,xobp,brl,brl_percent,exit_velocity,max_ev,hard_hit_percent,k_percent,bb_percent,whiff_percent,chase_percent,arm_strength,sprint_speed,oaa,bat_speed,squared_up_rate\n"
    "Shohei Ohtani,660271,2024,99,95,99,99,97,100,100,99,100,99,44,85,60,70,80,75,50,97,88\n"
    "Mike Trout,545361,2024,95,85,95,95,90,90,90,95,95,92,50,90,55,65,70,60,55,90,80\n"
)

_MOCK_PERCENTILES_PITCHER = (
    "player_name,player_id,year,xwoba,xba,xslg,xiso,xobp,brl,brl_percent,exit_velocity,max_ev,hard_hit_percent,k_percent,bb_percent,whiff_percent,chase_percent,arm_strength,xera,fb_velocity,fb_spin,curve_spin\n"
    "Shohei Ohtani,660271,2023,90,88,89,85,87,85,85,88,90,86,92,60,89,80,95,91,95,80,75\n"
    "Paul Skenes,694973,2024,98,92,95,90,91,92,92,94,96,93,98,75,95,85,99,97,99,85,90\n"
)

_MOCK_EXPECTED_STATS_BATTER = (
    "last_name, first_name,player_id,year,pa,bip,ba,est_ba,est_ba_minus_ba_diff,slg,est_slg,est_slg_minus_slg_diff,woba,est_woba,est_woba_minus_woba_diff\n"
    "Ohtani, Shohei,660271,2024,731,450,.310,.295,-.015,.646,.620,-.026,.425,.444,.019\n"
    "Trout, Mike,545361,2024,120,70,.220,.250,.030,.541,.510,-.031,.330,.350,.020\n"
)

_MOCK_STATCAST_EV_BATTER = (
    "last_name, first_name,player_id,attempts,avg_hit_angle,anglesweetspotpercent,max_hit_speed,avg_hit_speed,ev50,fbld,gb,max_distance,avg_distance,avg_hr_distance,ev95plus,ev95percent,barrels,brl_percent,brl_pa\n"
    "Ohtani, Shohei,660271,400,15.2,38.5,119.2,95.8,102.5,98.1,91.0,470,230,425,240,60.1,103,21.5,14.1\n"
    "Trout, Mike,545361,65,16.0,35.0,114.5,92.5,99.0,95.0,88.0,450,220,410,35,53.8,12,18.5,10.0\n"
)

_MOCK_BAT_TRACKING = (
    "id,name,side,avg_bat_speed,swing_tilt,attack_angle,attack_direction,ideal_attack_angle_rate,avg_intercept_y_vs_plate,avg_intercept_y_vs_batter,avg_batter_y_position,avg_batter_x_position,competitive_swings\n"
    "660271,Ohtani Shohei,L,76.3,30.5,12.5,0.2,25.4,1.5,2.1,0.5,0.2,600\n"
    "545361,Trout Mike,R,74.5,31.0,11.8,-0.1,24.0,1.4,2.0,0.5,0.1,100\n"
)

_MOCK_SPRINT_SPEED = (
    "last_name, first_name,player_id,team_id,team,position,age,competitive_runs,bolts,hp_to_1b,sprint_speed\n"
    "Ohtani, Shohei,660271,119,LAD,DH,30,85,15,4.10,28.1\n"
    "Trout, Mike,545361,108,LAA,CF,32,15,2,4.25,27.5\n"
)

_MOCK_PITCH_ARSENAL_SPEED = (
    "last_name, first_name,pitcher,ff_avg_speed,si_avg_speed,fc_avg_speed,sl_avg_speed,ch_avg_speed,cu_avg_speed,fs_avg_speed,kn_avg_speed,st_avg_speed,sv_avg_speed\n"
    "Skenes, Paul,694973,99.1,98.5,,86.0,,84.5,94.2,,,\n"
)

_MOCK_PITCH_ARSENAL_SPIN = (
    "last_name, first_name,pitcher,ff_avg_spin,si_avg_spin,fc_avg_spin,sl_avg_spin,ch_avg_spin,cu_avg_spin,fs_avg_spin,kn_avg_spin,st_avg_spin,sv_avg_spin\n"
    "Skenes, Paul,694973,2350,2280,,2500,,2650,2100,,,\n"
)

_MOCK_PITCH_ARSENAL_STATS = (
    "last_name, first_name,player_id,team_name_alt,pitch_type,pitch_name,run_value_per_100,run_value,pitches,pitch_usage,pa,ba,slg,woba,whiff_percent,k_percent,put_away,est_ba,est_slg,est_woba,hard_hit_percent\n"
    "Skenes, Paul,694973,PIT,FF,4-Seam Fastball,1.5,12,1100,45.0,280,.180,.310,.250,28.5,32.0,25.0,.190,.320,.260,35.0\n"
    "Skenes, Paul,694973,PIT,FS,Splitter,2.1,8,700,30.0,170,.140,.200,.180,38.0,40.0,30.0,.150,.210,.190,28.0\n"
)


def _setup_mock_http(url_map: dict[str, str]) -> BaseballContext:
    mock_cache = MagicMock()
    mock_cache.get.return_value = None
    mock_cache.get_or_fetch = AsyncMock(side_effect=_mock_fetch)
    mock_http = AsyncMock(spec=HttpClient)

    async def _get_text(url: str, params: dict[str, str] | None = None, **kwargs: object) -> str:
        if "/leaderboard/percentile-rankings" in url and params is not None:
            ptype = params.get("type", "batter")
            key = f"/leaderboard/percentile-rankings?type={ptype}"
            if key in url_map:
                return url_map[key]
        for path_key, csv_content in url_map.items():
            if path_key in url:
                return csv_content
        return ""

    mock_http.get_text = AsyncMock(side_effect=_get_text)
    return BaseballContext(http=mock_http, cache=mock_cache)


@pytest.mark.asyncio
async def test_composite_percentile_ranks_batter() -> None:
    url_map = {
        "/leaderboard/percentile-rankings": _MOCK_PERCENTILES_BATTER,
        "/leaderboard/expected_statistics": _MOCK_EXPECTED_STATS_BATTER,
        "/leaderboard/statcast": _MOCK_STATCAST_EV_BATTER,
        "/leaderboard/bat-tracking": _MOCK_BAT_TRACKING,
        "/leaderboard/sprint_speed": _MOCK_SPRINT_SPEED,
    }
    ctx = _setup_mock_http(url_map)

    df = await statcast_composite_percentile_ranks(2024, player_type="batter", context=ctx)
    assert isinstance(df, pl.DataFrame)
    assert df.height == 2
    assert "player_id" in df.columns
    assert "player_name" in df.columns
    assert "xwoba_percentile" in df.columns
    assert "xwoba_raw" in df.columns
    assert "exit_velocity_percentile" in df.columns
    assert "exit_velocity_raw" in df.columns
    assert "bat_speed_raw" in df.columns
    assert "sprint_speed_raw" in df.columns

    ohtani = df.filter(pl.col("player_id") == 660271)
    assert ohtani["xwoba_percentile"][0] == 99
    assert ohtani["xwoba_raw"][0] == pytest.approx(0.444)
    assert ohtani["exit_velocity_raw"][0] == pytest.approx(95.8)
    assert ohtani["max_ev_raw"][0] == pytest.approx(119.2)
    assert ohtani["bat_speed_raw"][0] == pytest.approx(76.3)
    assert ohtani["sprint_speed_raw"][0] == pytest.approx(28.1)


@pytest.mark.asyncio
async def test_player_percentile_profile_batter() -> None:
    url_map = {
        "/leaderboard/percentile-rankings": _MOCK_PERCENTILES_BATTER,
        "/leaderboard/expected_statistics": _MOCK_EXPECTED_STATS_BATTER,
        "/leaderboard/statcast": _MOCK_STATCAST_EV_BATTER,
        "/leaderboard/bat-tracking": _MOCK_BAT_TRACKING,
        "/leaderboard/sprint_speed": _MOCK_SPRINT_SPEED,
    }
    ctx = _setup_mock_http(url_map)

    profile = await statcast_player_percentile_profile(660271, 2024, player_type="batter", context=ctx)
    assert isinstance(profile, pl.DataFrame)
    assert profile.columns == ["metric", "label", "percentile", "raw_value", "unit"]
    assert profile.schema["raw_value"] == pl.Float64
    assert profile.schema["percentile"] == pl.Int64

    metrics = dict(zip(profile["metric"].to_list(), profile["raw_value"].to_list(), strict=False))
    assert metrics.get("xwoba") == pytest.approx(0.444)
    assert metrics.get("exit_velocity") == pytest.approx(95.8)
    assert metrics.get("max_ev") == pytest.approx(119.2)
    assert metrics.get("bat_speed") == pytest.approx(76.3)
    assert metrics.get("sprint_speed") == pytest.approx(28.1)


@pytest.mark.asyncio
async def test_player_percentile_profile_fallback_to_pitcher() -> None:
    # Player not in batter percentiles, but in pitcher percentiles
    url_map = {
        "/leaderboard/percentile-rankings?type=batter": "player_name,player_id,year\n",
        "/leaderboard/percentile-rankings?type=pitcher": _MOCK_PERCENTILES_PITCHER,
        "/leaderboard/pitch-arsenals": _MOCK_PITCH_ARSENAL_SPEED,
    }
    ctx = _setup_mock_http(url_map)

    # When player_type is None, tries batter first (empty), falls back to pitcher
    profile = await statcast_player_percentile_profile(694973, 2024, player_type=None, context=ctx)
    assert isinstance(profile, pl.DataFrame)
    assert profile.columns == ["metric", "label", "percentile", "raw_value", "unit"]
    assert profile.height > 0
    assert "xera" in profile["metric"].to_list() or "fb_velocity" in profile["metric"].to_list()


@pytest.mark.asyncio
async def test_player_percentile_profile_empty_returns_empty_dataframe() -> None:
    url_map = {
        "/leaderboard/percentile-rankings": _MOCK_PERCENTILES_BATTER,
    }
    ctx = _setup_mock_http(url_map)

    profile = await statcast_player_percentile_profile(999999, 2024, player_type="batter", context=ctx)
    assert isinstance(profile, pl.DataFrame)
    assert profile.height == 0
    assert profile.columns == ["metric", "label", "percentile", "raw_value", "unit"]


@pytest.mark.asyncio
async def test_invalid_player_type_raises_error() -> None:
    from polars_baseball.exceptions import InvalidParameterError

    ctx = _setup_mock_http({})
    with pytest.raises(InvalidParameterError, match="player_type"):
        await statcast_composite_percentile_ranks(2024, player_type="invalid", context=ctx)  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_composite_percentile_ranks_historical_year() -> None:
    url_map = {
        "/leaderboard/percentile-rankings": _MOCK_PERCENTILES_BATTER,
        "/leaderboard/expected_statistics": _MOCK_EXPECTED_STATS_BATTER,
        "/leaderboard/statcast": _MOCK_STATCAST_EV_BATTER,
    }
    ctx = _setup_mock_http(url_map)

    # 2020: before bat tracking (2024)
    df = await statcast_composite_percentile_ranks(2020, player_type="batter", context=ctx)
    assert isinstance(df, pl.DataFrame)
    assert "bat_speed_raw" in df.columns
    # bat_speed_raw should be all nulls
    assert df["bat_speed_raw"].is_null().all()
