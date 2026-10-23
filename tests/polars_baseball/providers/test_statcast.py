from unittest.mock import AsyncMock, patch

import polars as pl
import pytest

from polars_baseball._client import HttpClient
from polars_baseball.client import BaseballClient
from polars_baseball.exceptions import InvalidParameterError, UpstreamUnavailableError

_default_client = BaseballClient()


async def statcast(
    *args: object, client: BaseballClient | None = None, context: BaseballClient | None = None, **kwargs: object
) -> pl.DataFrame:
    c = client or context or _default_client
    return await c.savant.statcast(*args, **kwargs)  # type: ignore[arg-type]


async def statcast_batter(
    *args: object, client: BaseballClient | None = None, context: BaseballClient | None = None, **kwargs: object
) -> pl.DataFrame:
    c = client or context or _default_client
    return await c.savant.batter(*args, **kwargs)  # type: ignore[arg-type]


async def statcast_pitcher(
    *args: object, client: BaseballClient | None = None, context: BaseballClient | None = None, **kwargs: object
) -> pl.DataFrame:
    c = client or context or _default_client
    return await c.savant.pitcher(*args, **kwargs)  # type: ignore[arg-type]


async def statcast_single_game(
    *args: object, client: BaseballClient | None = None, context: BaseballClient | None = None, **kwargs: object
) -> pl.DataFrame:
    c = client or context or _default_client
    return await c.savant.single_game(*args, **kwargs)  # type: ignore[arg-type]


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
async def test_statcast_single_game(mock_statcast_csv: str) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=mock_statcast_csv)
    client = BaseballClient(http=mock_http)

    df = await statcast_single_game(123456, client=client)
    assert isinstance(df, pl.DataFrame)
    assert df.height == 2
    assert df["game_pk"][0] == 123456
    assert df["pitch_type"][0] == "SL"
    assert df["pitch_type"][1] == "FF"


@pytest.mark.asyncio
async def test_statcast_date_range() -> None:
    mock_http = AsyncMock(spec=HttpClient)
    csv_part1 = (
        "game_date,game_pk,at_bat_number,pitch_number,pitch_type,release_speed\n"
        "2026-06-01,123456,1,1,FF,95.5\n"
        "2026-06-01,123456,1,2,SL,84.2\n"
    )
    csv_part2 = "game_date,game_pk,at_bat_number,pitch_number,pitch_type,release_speed\n2026-06-08,123457,2,1,FF,98.1\n"
    mock_http.get_text = AsyncMock(side_effect=[csv_part1, csv_part2])
    client = BaseballClient(http=mock_http)

    df = await statcast(start_date="2026-06-01", end_date="2026-06-08", verbose=False, client=client)
    assert isinstance(df, pl.DataFrame)
    assert df.height == 3
    assert df["game_date"][0] == "2026-06-08"
    assert df["game_date"][1] == "2026-06-01"
    assert df["pitch_number"][1] == 2
    assert df["pitch_number"][2] == 1


@pytest.mark.asyncio
async def test_statcast_accepts_date_parameters(
    mock_statcast_csv: str,
) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=mock_statcast_csv)
    client = BaseballClient(http=mock_http)

    df = await statcast(start_date="2026-06-01", end_date="2026-06-01", verbose=False, client=client)
    assert isinstance(df, pl.DataFrame)
    assert df.height == 2


@pytest.mark.asyncio
async def test_statcast_player_lookups(mock_statcast_csv: str) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=mock_statcast_csv)
    client = BaseballClient(http=mock_http)

    df_bat = await statcast_batter(start_date="2026-06-01", end_date="2026-06-01", player_id=123456, client=client)
    assert isinstance(df_bat, pl.DataFrame)
    assert df_bat.height == 2
    assert df_bat["game_pk"][0] == 123456

    df_pit = await statcast_pitcher(start_date="2026-06-01", end_date="2026-06-01", player_id=123456, client=client)
    assert isinstance(df_pit, pl.DataFrame)
    assert df_pit.height == 2
    assert df_pit["game_pk"][0] == 123456

    with pytest.raises(InvalidParameterError):
        await statcast_batter(start_date="2026-06-01", end_date="2026-06-01", player_id=None)


@pytest.mark.asyncio
async def test_statcast_single_game_empty_returns_dataframe() -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value="game_date,game_pk,pitch_type\n")
    client = BaseballClient(http=mock_http)

    result = await statcast_single_game(999999, client=client)

    assert isinstance(result, pl.DataFrame)
    assert result.is_empty()


@pytest.mark.asyncio
async def test_statcast_single_game_no_response_raises() -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value="")

    with pytest.raises(UpstreamUnavailableError):
        await statcast_single_game(999999, client=BaseballClient(http=mock_http))


@pytest.mark.asyncio
@patch("polars_baseball.savant.SavantGateway.get_dataset")
async def test_statcast_player_cross_year_with_empty_chunk(
    mock_get_dataset: AsyncMock,
) -> None:
    """When cross-year chunks are queried, empty chunks should be safely ignored."""
    df_2025 = pl.DataFrame({"game_date": ["2025-06-01"], "game_pk": [111], "at_bat_number": [1], "pitch_number": [1]})
    df_2026 = pl.DataFrame()
    mock_get_dataset.side_effect = [df_2025, df_2026]
    client = BaseballClient()

    df = await statcast_batter(start_date="2025-06-01", end_date="2026-06-01", player_id=123456, client=client)

    assert isinstance(df, pl.DataFrame)
    assert df.height == 1
    assert df["game_date"][0] == "2025-06-01"


def test_align_schemas() -> None:
    from polars_baseball._schemas.statcast import align_statcast_schemas as _align_schemas

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

    # 3. Test unknown mixed string and numeric conflict (should safely align to String, not Float64)
    df_str = pl.DataFrame({"custom_code": pl.Series(["K", "BB"], dtype=pl.String)})
    df_num = pl.DataFrame({"custom_code": pl.Series([1, 2], dtype=pl.Int64)})
    aligned_mixed = _align_schemas([df_str, df_num])
    assert aligned_mixed[0]["custom_code"].dtype == pl.String
    assert aligned_mixed[1]["custom_code"].dtype == pl.String


@pytest.mark.asyncio
async def test_statcast_concat_path_with_schema_alignment() -> None:
    mock_http = AsyncMock(spec=HttpClient)

    csv_part1 = "game_date,game_pk,bat_speed,miss_distance\n2026-06-01,123456,70.5,1.2\n2026-06-02,123457,72.3,2.1\n"
    csv_part2 = "game_date,game_pk,bat_speed,miss_distance\n2026-06-08,123458,,\n"

    mock_http.get_text = AsyncMock(side_effect=[csv_part1, csv_part2])
    client = BaseballClient(http=mock_http)

    df = await statcast(start_date="2026-06-01", end_date="2026-06-08", verbose=False, client=client)

    assert isinstance(df, pl.DataFrame)
    assert df.height == 3
    # Verify that bat_speed and miss_distance have been aligned to Float64
    assert df["bat_speed"].dtype == pl.Float64
    assert df["miss_distance"].dtype == pl.Float64
    assert df["bat_speed"][0] is None  # descending sort (June 8th has None bat_speed)
    assert df["bat_speed"][2] == 70.5  # June 1st has 70.5 bat_speed


@pytest.mark.asyncio
async def test_statcast_parallel_uses_bounded_gather() -> None:
    from datetime import date

    date_range = [(date(2026, 4, 1), date(2026, 4, 7)), (date(2026, 4, 8), date(2026, 4, 14))]
    with patch("polars_baseball._savant._statcast.bounded_gather", new_callable=AsyncMock) as mock_bg:
        mock_bg.return_value = [pl.DataFrame(), pl.DataFrame()]
        client = BaseballClient()
        await client.savant._run_statcast_parallel(date_range, team=None, verbose=False, concurrency_limit=2)
        mock_bg.assert_called_once()
        tasks = mock_bg.call_args[0][0]
        assert len(tasks) == 2
        assert mock_bg.call_args[1]["concurrency_limit"] == 2


@pytest.mark.asyncio
async def test_statcast_parallel_bounds_task_admission() -> None:
    import asyncio
    from datetime import date

    active = 0
    peak = 0
    lock = asyncio.Lock()

    async def mock_small_request(
        start: date, end: date, team: str | None, client: object = None, context: object = None
    ) -> pl.DataFrame:
        nonlocal active, peak
        async with lock:
            active += 1
            if active > peak:
                peak = active
        await asyncio.sleep(0.01)
        async with lock:
            active -= 1
        return pl.DataFrame({"game_date": [str(start)], "game_pk": [100], "at_bat_number": [1], "pitch_number": [1]})

    date_range = [
        (date(2026, 4, 1), date(2026, 4, 7)),
        (date(2026, 4, 8), date(2026, 4, 14)),
        (date(2026, 4, 15), date(2026, 4, 21)),
        (date(2026, 4, 22), date(2026, 4, 28)),
    ]

    client = BaseballClient()
    with patch.object(client.savant, "_small_request", side_effect=mock_small_request):
        dfs = await client.savant._run_statcast_parallel(date_range, team=None, verbose=False, concurrency_limit=2)

    assert peak <= 2
    assert len(dfs) == 4


@pytest.mark.asyncio
async def test_statcast_parallel_verbose_progress() -> None:
    from datetime import date

    date_range = [(date(2026, 4, 1), date(2026, 4, 7)), (date(2026, 4, 8), date(2026, 4, 14))]
    client = BaseballClient()
    with patch.object(client.savant, "_small_request", new_callable=AsyncMock) as mock_req:
        mock_req.return_value = pl.DataFrame()
        dfs = await client.savant._run_statcast_parallel(date_range, team=None, verbose=True, concurrency_limit=2)

    assert len(dfs) == 2
