from typing import cast
from unittest.mock import AsyncMock, MagicMock

import polars as pl
import pytest

from polars_baseball._client import HttpClient
from polars_baseball.apis.savant_fielding_running import (
    statcast_arm_strength,
    statcast_baserunning_run_value,
    statcast_catcher_stance,
    statcast_catcher_throwing,
)
from polars_baseball.apis.savant_leaderboards import (
    statcast_batter_bat_tracking,
    statcast_batter_exitvelo_barrels,
    statcast_batter_expected_stats,
    statcast_batter_percentile_ranks,
    statcast_batter_pitch_arsenal,
    statcast_batter_run_value,
    statcast_pitch_tempo,
    statcast_pitcher_active_spin,
    statcast_pitcher_pitch_arsenal,
    statcast_pitcher_run_value,
    statcast_pitcher_spin_dir_comp,
)
from polars_baseball.context import BaseballContext
from polars_baseball.enums.savant import ArsenalType
from polars_baseball.exceptions import InvalidParameterError, UpstreamParseError

_MOCK_CSV = "player_name,player_id,year,stat_value\nOhtani Shohei,660271,2026,99.9\nTrout Mike,545361,2026,95.5\n"


async def _get_or_fetch(key: str, fetcher: object, **kwargs: object) -> pl.DataFrame:
    return await fetcher()  # type: ignore[misc]


@pytest.mark.asyncio
async def test_batter_leaderboards() -> None:
    mock_cache = MagicMock()
    mock_cache.get.return_value = None
    mock_cache.get_or_fetch = AsyncMock(side_effect=_get_or_fetch)
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text.return_value = _MOCK_CSV
    ctx = BaseballContext(http=mock_http, cache=mock_cache)

    df1 = await statcast_batter_exitvelo_barrels(2026, context=ctx)
    df2 = await statcast_batter_expected_stats(2026, context=ctx)
    df3 = await statcast_batter_pitch_arsenal(2026, context=ctx)
    df4 = await statcast_batter_bat_tracking(2026, context=ctx)

    assert isinstance(df1, pl.DataFrame)
    assert "player_name" in df1.columns
    assert df2.height == 2
    assert df3.height == 2
    assert df4.height == 2


@pytest.mark.asyncio
async def test_savant_leaderboard_empty_response_fails_fast() -> None:
    mock_cache = MagicMock()
    mock_cache.get.return_value = None
    mock_cache.get_or_fetch = AsyncMock(side_effect=_get_or_fetch)
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text.return_value = ""
    ctx = BaseballContext(http=mock_http, cache=mock_cache)

    with pytest.raises(UpstreamParseError, match="empty"):
        await statcast_batter_exitvelo_barrels(2026, context=ctx)


@pytest.mark.asyncio
async def test_percentile_ranks_filtering() -> None:
    mock_cache = MagicMock()
    mock_cache.get.return_value = None
    mock_cache.get_or_fetch = AsyncMock(side_effect=_get_or_fetch)
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text.return_value = "player_name,player_id,year\nOhtani Shohei,660271,2026\n,999999,2026\n"
    ctx = BaseballContext(http=mock_http, cache=mock_cache)

    df = await statcast_batter_percentile_ranks(2026, context=ctx)

    assert df.height == 1
    assert df["player_id"][0] == 660271


@pytest.mark.asyncio
async def test_run_values() -> None:
    mock_cache = MagicMock()
    mock_cache.get.return_value = None
    mock_cache.get_or_fetch = AsyncMock(side_effect=_get_or_fetch)
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text.return_value = _MOCK_CSV
    ctx = BaseballContext(http=mock_http, cache=mock_cache)

    df_bat = await statcast_batter_run_value(2026, context=ctx)
    df_pit = await statcast_pitcher_run_value(2026, context=ctx)

    assert isinstance(df_bat, pl.DataFrame)
    assert df_bat.height == 2
    assert isinstance(df_pit, pl.DataFrame)
    assert df_pit.height == 2


@pytest.mark.asyncio
async def test_active_spin_fallback() -> None:
    mock_cache = MagicMock()
    mock_cache.get.return_value = None
    mock_cache.get_or_fetch = AsyncMock(side_effect=_get_or_fetch)
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text.side_effect = [
        "<html><body>Redirecting...</body></html>",
        _MOCK_CSV,
    ]
    ctx = BaseballContext(http=mock_http, cache=mock_cache)

    with pytest.warns(UserWarning, match="spin-based"):
        df = await statcast_pitcher_active_spin(2020, context=ctx)

    assert isinstance(df, pl.DataFrame)
    assert df.height == 2
    assert mock_http.get_text.call_count == 2


@pytest.mark.asyncio
async def test_active_spin_raises_when_all_fetches_fail() -> None:
    mock_cache = MagicMock()
    mock_cache.get.return_value = None
    mock_cache.get_or_fetch = AsyncMock(side_effect=_get_or_fetch)
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text.return_value = "<html><body>Redirecting...</body></html>"
    ctx = BaseballContext(http=mock_http, cache=mock_cache)

    with pytest.warns(UserWarning, match="spin-based"):
        with pytest.raises(UpstreamParseError, match="active spin"):
            await statcast_pitcher_active_spin(2020, context=ctx)

    assert mock_http.get_text.call_count == 2


@pytest.mark.asyncio
async def test_pitch_arsenal_accepts_enum() -> None:
    mock_cache = MagicMock()
    mock_cache.get.return_value = None
    mock_cache.get_or_fetch = AsyncMock(side_effect=_get_or_fetch)
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text.return_value = _MOCK_CSV
    ctx = BaseballContext(http=mock_http, cache=mock_cache)

    df = await statcast_pitcher_pitch_arsenal(2026, arsenal_type=ArsenalType.AVG_SPEED, context=ctx)

    assert isinstance(df, pl.DataFrame)
    assert df.height == 2


@pytest.mark.asyncio
async def test_pitch_arsenal_rejects_raw_string() -> None:
    with pytest.raises(InvalidParameterError, match="arsenal_type must be an ArsenalType"):
        await statcast_pitcher_pitch_arsenal(2026, arsenal_type=cast(ArsenalType, "avg_speed"))


@pytest.mark.asyncio
async def test_spin_dir_comp_uses_params_dict() -> None:
    mock_cache = MagicMock()
    mock_cache.get.return_value = None
    mock_cache.get_or_fetch = AsyncMock(side_effect=_get_or_fetch)
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text.return_value = _MOCK_CSV
    ctx = BaseballContext(http=mock_http, cache=mock_cache)

    await statcast_pitcher_spin_dir_comp(2024, pitch_a="FF", pitch_b="CH", context=ctx)

    called_url = mock_http.get_text.call_args.args[0]
    called_params = mock_http.get_text.call_args.kwargs["params"]
    assert " " not in called_url
    assert called_params["type"] == "4-Seamer / Changeup"


@pytest.mark.asyncio
async def test_savant_leaderboard_robust_parsing() -> None:
    mock_cache = MagicMock()
    mock_cache.get.return_value = None
    mock_cache.get_or_fetch = AsyncMock(side_effect=_get_or_fetch)
    mock_http = AsyncMock(spec=HttpClient)
    # Return messy CSV with spaces in header and string values, and mixed formats
    mock_http.get_text.return_value = "player_name , player_id , year , stat \n Ohtani Shohei , 660271 , 2026 , 12.3 \n"
    ctx = BaseballContext(http=mock_http, cache=mock_cache)

    df = await statcast_batter_exitvelo_barrels(2026, context=ctx)
    assert "player_id" in df.columns  # Header stripped
    assert df["player_id"].dtype == pl.Int64  # Cast to Int64
    assert df["year"].dtype == pl.Int64  # Cast to Int64
    assert df["player_name"][0] == "Ohtani Shohei"  # Whitespace stripped from string values


@pytest.mark.asyncio
async def test_pitch_tempo() -> None:
    mock_cache = MagicMock()
    mock_cache.get.return_value = None
    mock_cache.get_or_fetch = AsyncMock(side_effect=_get_or_fetch)
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text.return_value = _MOCK_CSV
    ctx = BaseballContext(http=mock_http, cache=mock_cache)

    df = await statcast_pitch_tempo(2026, context=ctx)
    assert isinstance(df, pl.DataFrame)
    assert df.height == 2


@pytest.mark.asyncio
async def test_arm_strength() -> None:
    mock_cache = MagicMock()
    mock_cache.get.return_value = None
    mock_cache.get_or_fetch = AsyncMock(side_effect=_get_or_fetch)
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text.return_value = _MOCK_CSV
    ctx = BaseballContext(http=mock_http, cache=mock_cache)

    df = await statcast_arm_strength(2026, context=ctx)

    called_url = mock_http.get_text.call_args.args[0]
    called_params = mock_http.get_text.call_args.kwargs["params"]
    assert "/leaderboard/arm-strength" in called_url
    assert called_params["csv"] == "true"
    assert called_params["type"] == "player"
    assert called_params["year"] == "2026"
    assert called_params["min"] == "50"
    assert isinstance(df, pl.DataFrame)
    assert df.height == 2


@pytest.mark.asyncio
async def test_baserunning_run_value() -> None:
    mock_cache = MagicMock()
    mock_cache.get.return_value = None
    mock_cache.get_or_fetch = AsyncMock(side_effect=_get_or_fetch)
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text.return_value = _MOCK_CSV
    ctx = BaseballContext(http=mock_http, cache=mock_cache)

    df = await statcast_baserunning_run_value(2026, context=ctx)

    called_url = mock_http.get_text.call_args.args[0]
    called_params = mock_http.get_text.call_args.kwargs["params"]
    assert "/leaderboard/baserunning-run-value" in called_url
    assert called_params["csv"] == "true"
    assert called_params["year"] == "2026"
    assert called_params["min"] == "5"
    assert isinstance(df, pl.DataFrame)
    assert df.height == 2


@pytest.mark.asyncio
async def test_catcher_throwing() -> None:
    mock_cache = MagicMock()
    mock_cache.get.return_value = None
    mock_cache.get_or_fetch = AsyncMock(side_effect=_get_or_fetch)
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text.return_value = _MOCK_CSV
    ctx = BaseballContext(http=mock_http, cache=mock_cache)

    df = await statcast_catcher_throwing(2026, context=ctx)

    called_url = mock_http.get_text.call_args.args[0]
    called_params = mock_http.get_text.call_args.kwargs["params"]
    assert "/leaderboard/catcher-throwing" in called_url
    assert called_params["csv"] == "true"
    assert called_params["year"] == "2026"
    assert called_params["min_att"] == "5"
    assert isinstance(df, pl.DataFrame)
    assert df.height == 2


@pytest.mark.asyncio
async def test_catcher_stance() -> None:
    mock_cache = MagicMock()
    mock_cache.get.return_value = None
    mock_cache.get_or_fetch = AsyncMock(side_effect=_get_or_fetch)
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text.return_value = _MOCK_CSV
    ctx = BaseballContext(http=mock_http, cache=mock_cache)

    df = await statcast_catcher_stance(2026, context=ctx)

    called_url = mock_http.get_text.call_args.args[0]
    called_params = mock_http.get_text.call_args.kwargs["params"]
    assert "/leaderboard/catcher-stance" in called_url
    assert called_params["csv"] == "true"
    assert called_params["year"] == "2026"
    assert isinstance(df, pl.DataFrame)
    assert df.height == 2
