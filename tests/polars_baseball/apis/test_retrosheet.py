import json
from unittest.mock import AsyncMock

import polars as pl
import pytest

from polars_baseball._client import HttpClient
from polars_baseball._schemas.retrosheet import (
    GAMELOG_COLUMNS,
    PARK_CODE_COLUMNS,
    ROSTER_COLUMNS,
    SCHEDULE_COLUMNS,
)
from polars_baseball.apis.retrosheet import (
    park_codes,
    rosters,
    schedules,
    season_game_logs,
    world_series_logs,
)
from polars_baseball.context import BaseballContext
from polars_baseball.exceptions import ServerError


@pytest.fixture
def mock_seasons_contents() -> bytes:
    # Simulating GitHub API response for repo contents listing
    contents = [
        {"name": "GL2026.TXT", "path": "seasons/2026/GL2026.TXT"},
        {"name": "2026schedule.csv", "path": "seasons/2026/2026schedule.csv"},
        {"name": "BOS2026.ROS", "path": "seasons/2026/BOS2026.ROS"},
        {"name": "NYA2026.ROS", "path": "seasons/2026/NYA2026.ROS"},
    ]
    return json.dumps(contents).encode("utf-8")


@pytest.fixture
def mock_roster_data() -> bytes:
    # 7 columns: player_id, last_name, first_name, bats, throws, team, position
    return b"ohtans01,Ohtani,Shohei,L,R,LAA,DH\ntroutm01,Trout,Mike,R,R,LAA,CF\n"


def test_retrosheet_schema_columns_are_immutable() -> None:
    assert isinstance(GAMELOG_COLUMNS, tuple)
    assert isinstance(PARK_CODE_COLUMNS, tuple)
    assert isinstance(ROSTER_COLUMNS, tuple)
    assert isinstance(SCHEDULE_COLUMNS, tuple)


@pytest.mark.asyncio
async def test_retrosheet_rosters_uses_supplied_context(
    mock_seasons_contents: bytes,
    mock_roster_data: bytes,
) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(
        side_effect=[
            mock_seasons_contents,
            mock_roster_data,
            mock_roster_data,
        ]
    )
    ctx = BaseballContext(http=mock_http)

    df = await rosters(2026, context=ctx)

    assert df.height == 4
    assert df.columns == list(ROSTER_COLUMNS)
    assert mock_http.get_text.await_count == 3


@pytest.mark.asyncio
async def test_retrosheet_rosters(
    mock_seasons_contents: bytes,
    mock_roster_data: bytes,
) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(
        side_effect=[
            mock_seasons_contents,
            mock_roster_data,
            mock_roster_data,
        ]
    )
    ctx = BaseballContext(http=mock_http)

    df = await rosters(2026, context=ctx)
    assert isinstance(df, pl.DataFrame)
    # 2 rows per roster file * 2 files = 4 rows
    assert df.height == 4
    assert df.columns == [
        "player_id",
        "last_name",
        "first_name",
        "bats",
        "throws",
        "team",
        "position",
    ]


@pytest.mark.asyncio
async def test_retrosheet_park_codes() -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(
        return_value=b"park_id,name,nickname,city,state,open,close,league,notes\nBOS07,Fenway Park,Fenway,Boston,MA,1912,2026,AL,\n"
    )
    ctx = BaseballContext(http=mock_http)
    df = await park_codes(context=ctx)
    assert df.height == 1
    assert df["name"][0] == "Fenway Park"


@pytest.mark.asyncio
async def test_retrosheet_schedules(mock_seasons_contents: bytes) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(
        side_effect=[
            mock_seasons_contents,
            b"2026-04-01,0,Wed,NYA,AL,1,BOS,AL,1,D,,\n",
        ]
    )
    ctx = BaseballContext(http=mock_http)
    df = await schedules(2026, context=ctx)
    assert df.height == 1
    assert df.columns == list(SCHEDULE_COLUMNS)
    assert df["visiting_team"][0] == "NYA"


@pytest.mark.asyncio
async def test_retrosheet_game_logs(mock_seasons_contents: bytes) -> None:
    populated_values = ["20260401", "0", "Wed", "NYA", "AL", "1", "BOS", "AL", "1", "5", "4"]
    dummy_row = ",".join([*populated_values, *([""] * (len(GAMELOG_COLUMNS) - len(populated_values)))]).encode()
    dummy_row += b"\n"
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(
        side_effect=[
            mock_seasons_contents,
            dummy_row,
        ]
    )
    ctx = BaseballContext(http=mock_http)

    df = await season_game_logs(2026, context=ctx)
    assert df.height == 1
    assert df.columns == list(GAMELOG_COLUMNS)
    assert df["visiting_team"][0] == "NYA"
    assert df["visiting_score"][0] == 5


@pytest.mark.asyncio
async def test_world_series_logs() -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=b"20261025,0,Sun,NYA,AL,1,BOS,AL,1,5,4," + b"," * 150 + b"\n")
    ctx = BaseballContext(http=mock_http)
    df = await world_series_logs(context=ctx)
    assert df.height == 1


@pytest.mark.asyncio
async def test_retrosheet_empty_responses_raise(mock_seasons_contents: bytes) -> None:
    from polars_baseball.exceptions import UpstreamUnavailableError

    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=b"")
    ctx = BaseballContext(http=mock_http)

    with pytest.raises(UpstreamUnavailableError):
        await park_codes(context=ctx)

    mock_http.get_text = AsyncMock(side_effect=[mock_seasons_contents, b""])
    with pytest.raises(UpstreamUnavailableError):
        await schedules(2026, context=ctx)


@pytest.mark.asyncio
async def test_retrosheet_explicit_github_token() -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=b"[]")
    ctx = BaseballContext(http=mock_http, github_token="my-test-token")

    with pytest.raises(ServerError, match="Rosters not available for 2026"):
        await rosters(2026, context=ctx)

    assert mock_http.get_text.call_args[1]["headers"]["Authorization"] == "token my-test-token"


@pytest.mark.asyncio
async def test_rosters_fail_fast_cancellation() -> None:
    import asyncio

    mock_contents = json.dumps(
        [
            {"name": "BOS2026.ROS"},
            {"name": "NYA2026.ROS"},
        ]
    ).encode("utf-8")
    cancelled = False

    async def mock_get_text(url: str, **kwargs: object) -> bytes:
        nonlocal cancelled
        if "contents" in url:
            return mock_contents
        if "BOS" in url:
            raise RuntimeError("Upstream roster fetch failure")
        try:
            await asyncio.sleep(1.0)
            return b"troutm01,Trout,Mike,R,R,LAA,CF\n"
        except asyncio.CancelledError:
            cancelled = True
            raise

    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(side_effect=mock_get_text)
    ctx = BaseballContext(http=mock_http)

    with pytest.raises(RuntimeError, match="Upstream roster fetch failure"):
        await rosters(2026, context=ctx, concurrency_limit=2)

    assert cancelled is True


@pytest.mark.asyncio
async def test_rosters_bounded_concurrency_admission() -> None:
    import asyncio

    contents = [{"name": f"TM{i}2026.ROS"} for i in range(5)]
    mock_contents = json.dumps(contents).encode("utf-8")

    active = 0
    peak = 0
    lock = asyncio.Lock()

    async def mock_get_text(url: str, **kwargs: object) -> bytes:
        nonlocal active, peak
        if "contents" in url:
            return mock_contents
        async with lock:
            active += 1
            if active > peak:
                peak = active
        await asyncio.sleep(0.01)
        async with lock:
            active -= 1
        return b"troutm01,Trout,Mike,R,R,LAA,CF\n"

    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(side_effect=mock_get_text)
    ctx = BaseballContext(http=mock_http)

    limit = 2
    df = await rosters(2026, context=ctx, concurrency_limit=limit)

    assert isinstance(df, pl.DataFrame)
    assert peak <= limit
