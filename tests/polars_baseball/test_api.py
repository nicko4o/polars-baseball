from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest

from polars_baseball._cache import CacheAdapter
from polars_baseball._client import HttpClient
from polars_baseball.client import BaseballClient


@pytest.mark.asyncio
async def test_statcast_batter_api() -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value="pitcher,release_speed,pitch_type\n123456,95.5,FF\n")
    client = BaseballClient(http=mock_http)

    df = await client.savant.batter(start_date="2026-06-01", end_date="2026-06-02", player_id=123456)

    assert isinstance(df, pl.DataFrame)
    assert df.height == 1
    assert df["pitcher"][0] == 123456


@pytest.mark.asyncio
async def test_statcast_pitcher_api() -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value="pitcher,release_speed,pitch_type\n789012,84.2,SL\n")
    client = BaseballClient(http=mock_http)

    df = await client.savant.pitcher(start_date="2026-06-01", end_date="2026-06-02", player_id=789012)

    assert isinstance(df, pl.DataFrame)
    assert df.height == 1
    assert df["pitcher"][0] == 789012


@pytest.mark.asyncio
async def test_statcast_api_cache_hit() -> None:
    cached_df = pl.DataFrame({"pitcher": [111], "release_speed": [99.9], "pitch_type": ["FF"]})
    mock_cache = MagicMock(spec=CacheAdapter)
    mock_cache.get_or_fetch = AsyncMock(return_value=cached_df)
    client = BaseballClient(cache=mock_cache)

    df = await client.savant.batter(
        start_date="2026-06-01",
        end_date="2026-06-02",
        player_id=111,
    )

    assert isinstance(df, pl.DataFrame)
    assert df.equals(cached_df)


@pytest.mark.asyncio
async def test_top_prospects_api_export() -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(
        return_value="<html><body><table><thead><tr><th>Rk</th><th>Player</th><th>Tm</th><th>Pos</th></tr></thead><tbody><tr><td>1</td><td>Adley Rutschman</td><td>BAL</td><td>C</td></tr></tbody></table></body></html>"
    )
    client = BaseballClient(http=mock_http)
    with patch.object(client.mlb, "resolve_team_id", new_callable=AsyncMock) as mock_resolve_team_id:
        mock_resolve_team_id.return_value = 110
        df = await client.mlb.top_prospects(team_name="Orioles")

    assert isinstance(df, pl.DataFrame)
    assert df.height == 1
    assert df["Player"][0] == "Adley Rutschman"
