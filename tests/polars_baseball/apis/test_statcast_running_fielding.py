from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest

from polars_baseball._client import HttpClient
from polars_baseball.apis.savant_fielding_running import (
    statcast_base_stealing,
    statcast_catcher_blocking,
    statcast_catcher_framing,
    statcast_catcher_poptime,
    statcast_fielding_run_value,
    statcast_outfield_catch_prob,
    statcast_outfield_directional_oaa,
    statcast_outfielder_jump,
    statcast_outs_above_average,
    statcast_running_splits,
    statcast_sprint_speed,
)
from polars_baseball.context import BaseballContext
from polars_baseball.exceptions import InvalidParameterError


@pytest.fixture
def mock_csv_data() -> bytes:
    return b"name,player_id,year,value\nOhtani Shohei,660271,2026,10.0\nTrout Mike,545361,2026,9.5\n"


@pytest.mark.asyncio
@patch("polars_baseball.apis._leaderboard_registry.default_context")
async def test_running_apis(mock_default_ctx: MagicMock, mock_csv_data: bytes) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=mock_csv_data)
    mock_default_ctx.return_value = BaseballContext(http=mock_http)

    # Sprint Speed
    df1 = await statcast_sprint_speed(2026)
    assert isinstance(df1, pl.DataFrame)
    assert df1.height == 2

    # Running Splits
    df2 = await statcast_running_splits(2026)
    assert df2.height == 2


@pytest.mark.asyncio
@patch("polars_baseball.apis._leaderboard_registry.default_context")
@patch("polars_baseball.apis.savant_leaderboards.default_context")
async def test_fielding_apis(mock_sl_ctx: MagicMock, mock_reg_ctx: MagicMock, mock_csv_data: bytes) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=mock_csv_data)
    mock_reg_ctx.return_value = BaseballContext(http=mock_http)
    mock_sl_ctx.return_value = BaseballContext(http=mock_http)

    # Outs Above Average (pos=3 is 1B, valid)
    df1 = await statcast_outs_above_average(2026, pos=3)
    assert df1.height == 2

    # Catcher pos=2 should raise InvalidParameterError for outs above average
    with pytest.raises(InvalidParameterError, match="This particular leaderboard does not include catchers"):
        await statcast_outs_above_average(2026, pos=2)

    # Fielding Run Value
    df2 = await statcast_fielding_run_value(2026, pos=3)
    assert df2.height == 2

    # Outfield Directional OAA
    df3 = await statcast_outfield_directional_oaa(2026)
    assert df3.height == 2

    # Outfield Catch Prob
    df4 = await statcast_outfield_catch_prob(2026)
    assert df4.height == 2

    # Outfielder Jump
    df5 = await statcast_outfielder_jump(2026)
    assert df5.height == 2

    # Catcher Poptime
    df6 = await statcast_catcher_poptime(2026)
    assert df6.height == 2


@pytest.mark.asyncio
@patch("polars_baseball.apis._leaderboard_registry.default_context")
@patch("polars_baseball.apis.savant_leaderboards.default_context")
async def test_oaa_fallback_on_html_response(mock_sl_ctx: MagicMock, mock_reg_ctx: MagicMock) -> None:
    """When Savant returns HTML instead of CSV for a valid pos, OAA should fall back to HTML table parsing."""
    html_data = b"""<!DOCTYPE html>
<html><head><title>Statcast Outs Above Average Leaderboard</title></head>
<body><div class="leaderboard-container">
<table id="leaderboard_table">
<thead><tr><th>player_id</th><th>player_name</th><th>team</th><th>pos</th><th>oaa</th><th>season</th></tr></thead>
<tbody>
<tr><td>660271</td><td><a href="/player/660271">Ohtani, Shohei</a></td><td>LAA</td><td>CF</td><td>10</td><td>2023</td></tr>
<tr><td>545361</td><td><a href="/player/545361">Trout, Mike</a></td><td>LAA</td><td>CF</td><td>8</td><td>2023</td></tr>
</tbody></table></div></body></html>"""
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=html_data)
    mock_reg_ctx.return_value = BaseballContext(http=mock_http)
    mock_sl_ctx.return_value = BaseballContext(http=mock_http)

    # pos="CF" (code=8) is valid; the mock returns HTML, triggering the HTML fallback path
    df = await statcast_outs_above_average(2023, pos="CF")
    assert isinstance(df, pl.DataFrame)
    assert df.height == 2
    assert "player_id" in df.columns
    assert "player_name" in df.columns


@pytest.mark.asyncio
async def test_oaa_rejects_aggregate_pos() -> None:
    """Aggregate position codes (IF, OF, ALL) must raise InvalidParameterError."""
    with pytest.raises(InvalidParameterError, match="aggregate code"):
        await statcast_outs_above_average(2023, pos="OF")

    with pytest.raises(InvalidParameterError, match="aggregate code"):
        await statcast_outs_above_average(2023, pos="IF")


@pytest.mark.asyncio
@patch("polars_baseball.apis._leaderboard_registry.default_context")
async def test_catcher_framing_filtering(mock_default_ctx: MagicMock) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=b"name,player_id,year,rv_tot\nRealmuto J.T.,592663,2026,10\n,,2026,0\n")
    mock_default_ctx.return_value = BaseballContext(http=mock_http)

    df = await statcast_catcher_framing(2026)
    assert df.height == 1
    assert df["player_id"][0] == 592663


@pytest.mark.asyncio
@patch("polars_baseball.apis._leaderboard_registry.default_context")
async def test_catcher_blocking_and_base_stealing(mock_default_ctx: MagicMock, mock_csv_data: bytes) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=mock_csv_data)
    mock_default_ctx.return_value = BaseballContext(http=mock_http)

    df_blocking = await statcast_catcher_blocking(2026)
    assert isinstance(df_blocking, pl.DataFrame)
    assert df_blocking.height == 2

    df_stealing = await statcast_base_stealing(2026)
    assert isinstance(df_stealing, pl.DataFrame)
    assert df_stealing.height == 2
