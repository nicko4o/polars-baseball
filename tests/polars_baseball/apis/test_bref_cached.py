from unittest.mock import MagicMock, patch

import polars as pl
import pytest

from polars_baseball._cache import GlobalCache
from polars_baseball.apis.bref import bwar_bat
from polars_baseball.context import BaseballContext


@pytest.mark.asyncio
@patch.object(GlobalCache, "set")
@patch.object(GlobalCache, "get")
async def test_bwar_bat_cache_hit(
    mock_cache_get: MagicMock,
    mock_cache_set: MagicMock,
) -> None:
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
    mock_cache_get.return_value = cached_df
    ctx = BaseballContext()

    df = await bwar_bat(context=ctx)

    assert df.height == 1
    assert "name_common" in df.columns
    assert "WAR" in df.columns
