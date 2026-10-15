from unittest.mock import AsyncMock, MagicMock

import polars as pl
import pytest

from polars_baseball._cache import CacheAdapter
from polars_baseball.client import BaseballClient


@pytest.mark.asyncio
async def test_bwar_bat_cache_hit() -> None:
    cached_df = pl.DataFrame(
        {
            "name_common": ["Mike Trout"],
            "mlb_ID": ["545361"],
            "player_ID": ["troutmi01"],
            "year_ID": [2023],
            "team_ID": ["LAA"],
            "WAR": [10.0],
        }
    )
    mock_cache = MagicMock(spec=CacheAdapter)
    mock_cache.get_or_fetch = AsyncMock(return_value=cached_df)
    client = BaseballClient(cache=mock_cache)

    df = await client.bref.bwar_bat()

    assert df.height == 1
    assert "name_common" in df.columns
    assert "WAR" in df.columns
