from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest

from polars_baseball import statcast, statcast_batter, statcast_pitcher
from polars_baseball._cache import GlobalCache
from polars_baseball._client import HttpClient
from polars_baseball.context import BaseballContext


@pytest.mark.asyncio
@patch.object(GlobalCache, "set")
@patch.object(GlobalCache, "get", return_value=None)
async def test_statcast_batter_api(
    mock_cache_get: MagicMock,
    mock_cache_set: MagicMock,
) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value="pitcher,release_speed,pitch_type\n123456,95.5,FF\n")
    ctx = BaseballContext(http=mock_http)

    df = await statcast_batter(start_dt="2026-06-01", end_dt="2026-06-02", player_id=123456, context=ctx)

    assert isinstance(df, pl.DataFrame)
    assert df.height == 1
    assert df["pitcher"][0] == 123456


@pytest.mark.asyncio
@patch.object(GlobalCache, "set")
@patch.object(GlobalCache, "get", return_value=None)
async def test_statcast_pitcher_api(
    mock_cache_get: MagicMock,
    mock_cache_set: MagicMock,
) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value="pitcher,release_speed,pitch_type\n789012,84.2,SL\n")
    ctx = BaseballContext(http=mock_http)

    df = await statcast_pitcher(start_dt="2026-06-01", end_dt="2026-06-02", player_id=789012, context=ctx)

    assert isinstance(df, pl.DataFrame)
    assert df.height == 1
    assert df["pitcher"][0] == 789012


@pytest.mark.asyncio
@patch.object(GlobalCache, "set")
@patch.object(GlobalCache, "get")
async def test_statcast_api_cache_hit(
    mock_cache_get: MagicMock,
    mock_cache_set: MagicMock,
) -> None:
    cached_df = pl.DataFrame({"pitcher": [111], "release_speed": [99.9], "pitch_type": ["FF"]})
    mock_cache_get.return_value = cached_df
    ctx = BaseballContext()

    df = await statcast_batter(
        start_dt="2026-06-01",
        end_dt="2026-06-02",
        player_id=111,
        context=ctx,
    )

    assert isinstance(df, pl.DataFrame)
    assert df.equals(cached_df)


@pytest.mark.asyncio
@patch("polars_baseball.apis.top_prospects.resolve_team_id")
async def test_top_prospects_api_export(mock_resolve_team_id: AsyncMock) -> None:
    from polars_baseball import top_prospects

    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(
        return_value="<html><body><table><thead><tr><th>Rk</th><th>Player</th><th>Tm</th><th>Pos</th></tr></thead><tbody><tr><td>1</td><td>Adley Rutschman</td><td>BAL</td><td>C</td></tr></tbody></table></body></html>"
    )
    mock_resolve_team_id.return_value = 110

    df = await top_prospects(team_name="Orioles", context=BaseballContext(http=mock_http))
    assert isinstance(df, pl.DataFrame)
    assert df.height == 1
    assert df["Player"][0] == "Adley Rutschman"


@pytest.mark.asyncio
@patch.object(GlobalCache, "set")
@patch.object(GlobalCache, "get", return_value=None)
async def test_statcast_deprecated_start_dt(
    mock_cache_get: MagicMock,
    mock_cache_set: MagicMock,
) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value="pitcher,release_speed,pitch_type\n123456,95.5,FF\n")
    ctx = BaseballContext(http=mock_http)

    with pytest.warns(DeprecationWarning, match="start_dt"):
        df = await statcast(start_dt="2026-06-01", end_dt="2026-06-02", verbose=False, context=ctx)

    assert isinstance(df, pl.DataFrame)
    assert df.height == 1
