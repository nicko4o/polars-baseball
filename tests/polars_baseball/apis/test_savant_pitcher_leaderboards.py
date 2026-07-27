from collections.abc import Callable
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import polars as pl
import pytest

from polars_baseball._client import HttpClient
from polars_baseball.apis.savant_leaderboards import (
    statcast_exitvelo_barrels,
    statcast_pitcher_bat_tracking,
    statcast_pitcher_exitvelo_barrels,
    statcast_pitcher_expected_stats,
    statcast_pitcher_percentile_ranks,
    statcast_pitcher_pitch_movement,
)
from polars_baseball.context import BaseballContext
from polars_baseball.enums.pitch import norm_pitch_code

_MOCK_CSV = "player_name,player_id,year,stat_value\nOhtani Shohei,660271,2026,99.9\nTrout Mike,545361,2026,95.5\n"


async def _get_or_fetch(key: str, fetcher: Callable[[], Any], **kwargs: object) -> Any:
    return await fetcher()


@pytest.mark.asyncio
async def test_pitcher_exitvelo_barrels() -> None:
    mock_cache = MagicMock()
    mock_cache.get.return_value = None
    mock_cache.get_or_fetch = AsyncMock(side_effect=_get_or_fetch)
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text.return_value = _MOCK_CSV
    ctx = BaseballContext(http=mock_http, cache=mock_cache)

    df = await statcast_pitcher_exitvelo_barrels(2026, context=ctx)

    assert isinstance(df, pl.DataFrame)
    assert df.height == 2
    assert "player_name" in df.columns


@pytest.mark.asyncio
async def test_pitcher_expected_stats() -> None:
    mock_cache = MagicMock()
    mock_cache.get.return_value = None
    mock_cache.get_or_fetch = AsyncMock(side_effect=_get_or_fetch)
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text.return_value = _MOCK_CSV
    ctx = BaseballContext(http=mock_http, cache=mock_cache)

    df = await statcast_pitcher_expected_stats(2026, context=ctx)

    assert isinstance(df, pl.DataFrame)
    assert df.height == 2


@pytest.mark.asyncio
async def test_pitcher_bat_tracking() -> None:
    mock_cache = MagicMock()
    mock_cache.get.return_value = None
    mock_cache.get_or_fetch = AsyncMock(side_effect=_get_or_fetch)
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text.return_value = _MOCK_CSV
    ctx = BaseballContext(http=mock_http, cache=mock_cache)

    df = await statcast_pitcher_bat_tracking(2026, context=ctx)

    assert isinstance(df, pl.DataFrame)
    assert df.height == 2


@pytest.mark.asyncio
async def test_pitcher_percentile_ranks() -> None:
    mock_cache = MagicMock()
    mock_cache.get.return_value = None
    mock_cache.get_or_fetch = AsyncMock(side_effect=_get_or_fetch)
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text.return_value = "player_name,player_id,year\nOhtani Shohei,660271,2026\n,999999,2026\n"
    ctx = BaseballContext(http=mock_http, cache=mock_cache)

    df = await statcast_pitcher_percentile_ranks(2026, context=ctx)

    assert df.height == 1
    assert df["player_id"][0] == 660271


@pytest.mark.asyncio
async def test_pitcher_pitch_movement() -> None:
    mock_cache = MagicMock()
    mock_cache.get.return_value = None
    mock_cache.get_or_fetch = AsyncMock(side_effect=_get_or_fetch)
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text.return_value = _MOCK_CSV
    ctx = BaseballContext(http=mock_http, cache=mock_cache)

    df = await statcast_pitcher_pitch_movement(2026, context=ctx)

    assert isinstance(df, pl.DataFrame)
    assert df.height == 2
    called_params = mock_http.get_text.call_args.kwargs["params"]
    assert called_params["pitch_type"] == norm_pitch_code("FF")


@pytest.mark.asyncio
async def test_exitvelo_barrels_pitcher_type() -> None:
    mock_cache = MagicMock()
    mock_cache.get.return_value = None
    mock_cache.get_or_fetch = AsyncMock(side_effect=_get_or_fetch)
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text.return_value = _MOCK_CSV
    ctx = BaseballContext(http=mock_http, cache=mock_cache)

    df = await statcast_exitvelo_barrels(2026, player_type="pitcher", context=ctx)

    assert isinstance(df, pl.DataFrame)
    assert df.height == 2


@pytest.mark.asyncio
async def test_pitcher_leaderboard_empty_response() -> None:
    mock_cache = MagicMock()
    mock_cache.get.return_value = None
    mock_cache.get_or_fetch = AsyncMock(side_effect=_get_or_fetch)
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text.return_value = ""
    ctx = BaseballContext(http=mock_http, cache=mock_cache)

    from polars_baseball.exceptions import UpstreamUnavailableError

    with pytest.raises(UpstreamUnavailableError, match="empty"):
        await statcast_pitcher_exitvelo_barrels(2026, context=ctx)
