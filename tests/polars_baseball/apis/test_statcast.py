from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest

from polars_baseball import statcast, statcast_single_game
from polars_baseball._client import HttpClient
from polars_baseball.apis.statcast import statcast_batter, statcast_pitcher
from polars_baseball.context import BaseballContext
from polars_baseball.exceptions import InvalidParameterError


@pytest.fixture
def mock_statcast_csv() -> str:
    # Minimal Statcast columns
    return (
        "game_date,game_pk,at_bat_number,pitch_number,pitch_type,release_speed\n"
        "2026-06-01,123456,1,1,FF,95.5\n"
        "2026-06-01,123456,1,2,SL,84.2\n"
    )


@pytest.fixture
def mock_statcast_csv_game2() -> str:
    return "game_date,game_pk,at_bat_number,pitch_number,pitch_type,release_speed\n2026-06-02,123457,2,1,FF,98.1\n"


@pytest.mark.asyncio
@patch("polars_baseball.apis.statcast.default_context")
async def test_statcast_single_game(mock_default_ctx: MagicMock, mock_statcast_csv: str) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=mock_statcast_csv)
    mock_default_ctx.return_value = BaseballContext(http=mock_http)

    df = await statcast_single_game(123456)
    assert isinstance(df, pl.DataFrame)
    assert df.height == 2
    assert df["game_pk"][0] == 123456
    assert df["pitch_type"][0] == "SL"
    assert df["pitch_type"][1] == "FF"


@pytest.mark.asyncio
@patch("polars_baseball.apis.statcast.default_context")
@patch("polars_baseball._cache.global_cache.get")
@patch("polars_baseball._cache.global_cache.set")
async def test_statcast_date_range(
    mock_cache_set: AsyncMock,
    mock_cache_get: AsyncMock,
    mock_default_ctx: MagicMock,
    mock_statcast_csv: str,
    mock_statcast_csv_game2: str,
) -> None:
    mock_cache_get.return_value = None
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(side_effect=[mock_statcast_csv, mock_statcast_csv_game2])
    mock_default_ctx.return_value = BaseballContext(http=mock_http)

    # Query 2 days (June 1st to June 2nd, 2026)
    df = await statcast(start_dt="2026-06-01", end_dt="2026-06-02", verbose=False)
    assert df.height == 3
    # Check that sorting is descending by game_date, game_pk, at_bat_number, pitch_number
    assert df["game_date"][0] == "2026-06-02"
    assert df["game_date"][1] == "2026-06-01"
    assert df["pitch_number"][1] == 2
    assert df["pitch_number"][2] == 1


@pytest.mark.asyncio
@patch("polars_baseball.apis.statcast.default_context")
async def test_statcast_player_lookups(mock_default_ctx: MagicMock, mock_statcast_csv: str) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=mock_statcast_csv)
    mock_default_ctx.return_value = BaseballContext(http=mock_http)

    df_bat = await statcast_batter(start_dt="2026-06-01", end_dt="2026-06-01", player_id=123456)
    assert df_bat.height == 2
    assert df_bat["game_pk"][0] == 123456

    df_pit = await statcast_pitcher(start_dt="2026-06-01", end_dt="2026-06-01", player_id=123456)
    assert df_pit.height == 2
    assert df_pit["game_pk"][0] == 123456

    with pytest.raises(InvalidParameterError):
        await statcast_batter(start_dt="2026-06-01", end_dt="2026-06-01", player_id=None)


@pytest.mark.asyncio
@patch("polars_baseball.apis.statcast.default_context")
async def test_statcast_single_game_empty_returns_dataframe(mock_default_ctx: MagicMock) -> None:
    """Empty game results should return an empty DataFrame instead of None."""
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value="game_date,game_pk,pitch_type\n")
    mock_default_ctx.return_value = BaseballContext(http=mock_http)

    result = await statcast_single_game(999999)

    assert isinstance(result, pl.DataFrame), f"Expected DataFrame, got {type(result)}"
    assert result.is_empty()


@pytest.mark.asyncio
@patch("polars_baseball.apis.statcast.default_context")
async def test_statcast_single_game_no_response_returns_dataframe(mock_default_ctx: MagicMock) -> None:
    """No HTTP response should return an empty DataFrame instead of None."""
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value="")
    mock_default_ctx.return_value = BaseballContext(http=mock_http)

    result = await statcast_single_game(999999)

    assert isinstance(result, pl.DataFrame), f"Expected DataFrame, got {type(result)}"


@pytest.mark.asyncio
async def test_statcast_oversize_warning() -> None:
    """Querying over 42 days should raise an oversize request warning."""
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value="game_date,game_pk\n2026-06-01,123\n")
    ctx = BaseballContext(http=mock_http)

    with pytest.warns(UserWarning, match="That's a nice request you got there"):
        await statcast(start_dt="2026-06-01", end_dt="2026-07-16", verbose=False, context=ctx)


@pytest.mark.asyncio
@patch("polars_baseball.apis.statcast.SavantGateway.get_dataset")
async def test_statcast_player_cross_year_with_empty_chunk(
    mock_get_dataset: AsyncMock,
) -> None:
    """When cross-year chunks are queried, empty chunks should be safely ignored."""
    df_2025 = pl.DataFrame({"game_date": ["2025-06-01"], "game_pk": [111], "at_bat_number": [1], "pitch_number": [1]})
    df_2026 = pl.DataFrame()
    mock_get_dataset.side_effect = [df_2025, df_2026]

    df = await statcast_batter(start_dt="2025-06-01", end_dt="2026-06-01", player_id=123456)

    assert isinstance(df, pl.DataFrame)
    assert df.height == 1
    assert df["game_date"][0] == "2025-06-01"
