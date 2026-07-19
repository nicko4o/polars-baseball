from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest

from polars_baseball import statcast, statcast_single_game
from polars_baseball._client import HttpClient
from polars_baseball.apis.statcast import statcast_batter, statcast_pitcher
from polars_baseball.context import BaseballContext
from polars_baseball.exceptions import InvalidParameterError, UpstreamUnavailableError


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
) -> None:
    mock_cache_get.return_value = None
    mock_http = AsyncMock(spec=HttpClient)
    # 8 days → step=7 produces 2 sub-queries: (Jun 1-7), (Jun 8-8)
    csv_part1 = (
        "game_date,game_pk,at_bat_number,pitch_number,pitch_type,release_speed\n"
        "2026-06-01,123456,1,1,FF,95.5\n"
        "2026-06-01,123456,1,2,SL,84.2\n"
    )
    csv_part2 = "game_date,game_pk,at_bat_number,pitch_number,pitch_type,release_speed\n2026-06-08,123457,2,1,FF,98.1\n"
    mock_http.get_text = AsyncMock(side_effect=[csv_part1, csv_part2])
    mock_default_ctx.return_value = BaseballContext(http=mock_http)

    df = await statcast(start_dt="2026-06-01", end_dt="2026-06-08", verbose=False)
    assert df.height == 3
    assert df["game_date"][0] == "2026-06-08"
    assert df["game_date"][1] == "2026-06-01"
    assert df["pitch_number"][1] == 2
    assert df["pitch_number"][2] == 1


@pytest.mark.asyncio
@patch("polars_baseball.apis.statcast.default_context")
@patch("polars_baseball._cache.global_cache.get")
@patch("polars_baseball._cache.global_cache.set")
async def test_statcast_accepts_date_aliases(
    mock_cache_set: AsyncMock,
    mock_cache_get: AsyncMock,
    mock_default_ctx: MagicMock,
    mock_statcast_csv: str,
) -> None:
    mock_cache_get.return_value = None
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=mock_statcast_csv)
    mock_default_ctx.return_value = BaseballContext(http=mock_http)

    df = await statcast(start_date="2026-06-01", end_date="2026-06-01", verbose=False)

    assert df.height == 2
    mock_cache_set.assert_called_once()


@pytest.mark.asyncio
async def test_statcast_rejects_conflicting_date_aliases() -> None:
    with pytest.raises(InvalidParameterError, match="start_dt and start_date"):
        await statcast(start_dt="2026-06-01", start_date="2026-06-02", verbose=False)


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
async def test_statcast_single_game_no_response_raises(mock_default_ctx: MagicMock) -> None:
    """No HTTP response should raise UpstreamUnavailableError."""
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value="")
    mock_default_ctx.return_value = BaseballContext(http=mock_http)

    with pytest.raises(UpstreamUnavailableError):
        await statcast_single_game(999999)


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


def test_align_schemas() -> None:
    from polars_baseball.apis.statcast import _align_schemas

    # 1. Test physics columns (string/numeric conflict resolves to Float64)
    df1 = pl.DataFrame({"bat_speed": [70.5, 75.2], "game_pk": [123, 456]})
    df2 = pl.DataFrame({"bat_speed": ["", "null"], "game_pk": ["789", "101"]})  # game_pk is in overrides (Int64)
    df3 = pl.DataFrame({"bat_speed": [None, 72.1], "game_pk": [112, 113]})

    aligned = _align_schemas([df1, df2, df3])

    # bat_speed should be Float64
    assert aligned[0]["bat_speed"].dtype == pl.Float64
    assert aligned[1]["bat_speed"].dtype == pl.Float64
    assert aligned[2]["bat_speed"].dtype == pl.Float64
    assert aligned[1]["bat_speed"][0] is None

    # game_pk should be Int64 (as defined in SAVANT_SCHEMA_OVERRIDES) and NOT promoted to Float64
    assert aligned[0]["game_pk"].dtype == pl.Int64
    assert aligned[1]["game_pk"].dtype == pl.Int64
    assert aligned[2]["game_pk"].dtype == pl.Int64
    assert aligned[1]["game_pk"][0] == 789

    # 2. Test unknown integer conflict (should align to Int64 instead of Float64)
    df_int32 = pl.DataFrame({"unknown_int_col": pl.Series([1, 2], dtype=pl.Int32)})
    df_int64 = pl.DataFrame({"unknown_int_col": pl.Series([3, 4], dtype=pl.Int64)})
    aligned_ints = _align_schemas([df_int32, df_int64])
    assert aligned_ints[0]["unknown_int_col"].dtype == pl.Int64
    assert aligned_ints[1]["unknown_int_col"].dtype == pl.Int64


@pytest.mark.asyncio
@patch("polars_baseball.apis.statcast.default_context")
@patch("polars_baseball._cache.global_cache.get")
@patch("polars_baseball._cache.global_cache.set")
async def test_statcast_concat_path_with_schema_alignment(
    mock_cache_set: AsyncMock,
    mock_cache_get: AsyncMock,
    mock_default_ctx: MagicMock,
) -> None:
    """Verify public statcast() API endpoint triggers schema alignment when merging chunks with mismatched schemas."""
    mock_cache_get.return_value = None
    mock_http = AsyncMock(spec=HttpClient)

    # part 1 (Jun 1-7): bat_speed is Float64
    csv_part1 = "game_date,game_pk,bat_speed,miss_distance\n2026-06-01,123456,70.5,1.2\n2026-06-02,123457,72.3,2.1\n"
    # part 2 (Jun 8): bat_speed is empty string (making Polars infer it differently)
    csv_part2 = "game_date,game_pk,bat_speed,miss_distance\n2026-06-08,123458,,\n"

    mock_http.get_text = AsyncMock(side_effect=[csv_part1, csv_part2])
    mock_default_ctx.return_value = BaseballContext(http=mock_http)

    # Query 8 days to force 2 sub-queries with step=7
    df = await statcast(start_dt="2026-06-01", end_dt="2026-06-08", verbose=False)

    assert isinstance(df, pl.DataFrame)
    assert df.height == 3
    # Verify that bat_speed and miss_distance have been aligned to Float64
    assert df["bat_speed"].dtype == pl.Float64
    assert df["miss_distance"].dtype == pl.Float64
    assert df["bat_speed"][0] is None  # descending sort (June 8th has None bat_speed)
    assert df["bat_speed"][2] == 70.5  # June 1st has 70.5 bat_speed
