import json
from unittest.mock import AsyncMock, MagicMock, patch

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
@patch("polars_baseball.apis.retrosheet.default_context")
async def test_retrosheet_rosters_uses_supplied_context(
    mock_default_ctx: MagicMock,
    mock_seasons_contents: bytes,
    mock_roster_data: bytes,
) -> None:
    mock_default_ctx.side_effect = AssertionError("default_context must not be used when context is supplied")
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
@patch("polars_baseball.apis.retrosheet.default_context")
async def test_retrosheet_rosters(
    mock_default_ctx: MagicMock,
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
    mock_default_ctx.return_value = BaseballContext(http=mock_http)

    df = await rosters(2026)
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
@patch("polars_baseball.apis.retrosheet.default_context")
async def test_retrosheet_park_codes(mock_default_ctx: MagicMock) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(
        return_value=b"park_id,name,nickname,city,state,open,close,league,notes\nBOS07,Fenway Park,Fenway,Boston,MA,1912,2026,AL,\n"
    )
    mock_default_ctx.return_value = BaseballContext(http=mock_http)
    df = await park_codes()
    assert df.height == 1
    assert df["name"][0] == "Fenway Park"


@pytest.mark.asyncio
@patch("polars_baseball.apis.retrosheet.default_context")
async def test_retrosheet_schedules(mock_default_ctx: MagicMock, mock_seasons_contents: bytes) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(
        side_effect=[
            mock_seasons_contents,
            b"2026-04-01,0,Wed,NYA,AL,1,BOS,AL,1,D,,\n",
        ]
    )
    mock_default_ctx.return_value = BaseballContext(http=mock_http)
    df = await schedules(2026)
    assert df.height == 1
    assert df.columns == list(SCHEDULE_COLUMNS)
    assert df["visiting_team"][0] == "NYA"


@pytest.mark.asyncio
@patch("polars_baseball.apis.retrosheet.default_context")
async def test_retrosheet_game_logs(mock_default_ctx: MagicMock, mock_seasons_contents: bytes) -> None:
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
    mock_default_ctx.return_value = BaseballContext(http=mock_http)

    df = await season_game_logs(2026)
    assert df.height == 1
    assert df.columns == list(GAMELOG_COLUMNS)
    assert df["visiting_team"][0] == "NYA"
    assert df["visiting_score"][0] == 5


@pytest.mark.asyncio
@patch("polars_baseball.apis.retrosheet.default_context")
async def test_world_series_logs(mock_default_ctx: MagicMock) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=b"20261025,0,Sun,NYA,AL,1,BOS,AL,1,5,4," + b"," * 150 + b"\n")
    mock_default_ctx.return_value = BaseballContext(http=mock_http)
    df = await world_series_logs()
    assert df.height == 1
