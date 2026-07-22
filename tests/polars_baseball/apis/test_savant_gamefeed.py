import json
from collections.abc import Sequence
from unittest.mock import AsyncMock, MagicMock

import polars as pl
import pytest

from polars_baseball._client import HttpClient
from polars_baseball.apis.savant_gamefeed import (
    savant_gamefeed_exit_velocity,
    savant_gamefeed_exit_velocity_many,
    savant_gamefeed_pitch_data,
    savant_gamefeed_pitch_data_many,
)
from polars_baseball.context import BaseballContext
from polars_baseball.exceptions import InvalidParameterError, UpstreamParseError
from polars_baseball.parsers.savant_gamefeed import EXIT_VELOCITY_SCHEMA, PITCH_DATA_SCHEMA

_GAME_PK = 777001


def _gamefeed_payload() -> str:
    return json.dumps(
        {
            "exit_velocity": [
                {
                    "batter_name": "Ohtani Shohei",
                    "team_batting": "LAD",
                    "pitcher_name": "Strider Spencer",
                    "team_fielding": "ATL",
                    "events": "Home Run",
                    "launch_speed": 118.7,
                    "launch_angle": 28,
                    "hit_distance": 455,
                    "xba": 0.920,
                    "start_speed": 98.2,
                    "contextMetrics": {"homeRunBallparks": 30},
                }
            ],
            "home_pitchers": {
                "675916": [
                    {
                        "pitcher_name": "Strider Spencer",
                        "team_pitching": "ATL",
                        "batter_name": "Ohtani Shohei",
                        "team_batting": "LAD",
                        "pitch_name": "4-Seamer",
                        "pitch_type": "FF",
                        "description": "Swinging Strike",
                        "events": "",
                        "start_speed": 99.1,
                        "spin_rate": 2410,
                        "breakXInches": -8.1,
                        "breakZInducedInches": 18.4,
                    }
                ]
            },
            "away_pitchers": {
                "607192": [
                    {
                        "pitcher_name": "Glasnow Tyler",
                        "team_pitching": "LAD",
                        "batter_name": "Acuna Ronald",
                        "team_batting": "ATL",
                        "pitch_name": "Curveball",
                        "pitch_type": "CU",
                        "description": "Called Strike",
                        "events": "Strikeout",
                        "start_speed": 84.5,
                        "spin_rate": 2895,
                        "breakXInches": 7.2,
                        "inducedBreakZ": -9.8,
                    }
                ]
            },
        }
    )


def _context(raw_payload: str) -> BaseballContext:
    mock_cache = MagicMock()
    mock_cache.get.return_value = None

    async def _gof(key: str, fetcher: object, **kwargs: object) -> pl.DataFrame:
        return await fetcher()  # type: ignore[misc]

    mock_cache.get_or_fetch = AsyncMock(side_effect=_gof)
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text.return_value = raw_payload
    return BaseballContext(http=mock_http, cache=mock_cache)


@pytest.mark.asyncio
async def test_savant_gamefeed_exit_velocity_flattens_core_columns() -> None:
    df = await savant_gamefeed_exit_velocity(_GAME_PK, context=_context(_gamefeed_payload()))

    assert df.columns == [
        "game_pk",
        "batter_name",
        "team_batting",
        "pitcher_name",
        "team_fielding",
        "events",
        "launch_speed",
        "launch_angle",
        "hit_distance",
        "xba",
        "start_speed",
        "home_run_ballparks",
    ]
    assert df.height == 1
    assert df["game_pk"].dtype == pl.Int64
    assert df["launch_speed"].dtype == pl.Float64
    assert df["home_run_ballparks"].dtype == pl.Int64
    assert df["home_run_ballparks"][0] == 30


@pytest.mark.asyncio
async def test_savant_gamefeed_pitch_data_combines_pitcher_nodes() -> None:
    df = await savant_gamefeed_pitch_data(_GAME_PK, context=_context(_gamefeed_payload()))

    assert df.columns == [
        "game_pk",
        "pitcher_id",
        "pitcher_name",
        "team_pitching",
        "batter_name",
        "team_batting",
        "pitch_name",
        "pitch_type",
        "description",
        "events",
        "start_speed",
        "spin_rate",
        "break_x_inches",
        "break_z_induced_inches",
    ]
    assert df.height == 2
    assert df["pitcher_id"].dtype == pl.Int64
    assert df["pitcher_id"].to_list() == [675916, 607192]
    assert df["spin_rate"].dtype == pl.Int64
    assert df["break_x_inches"].dtype == pl.Float64
    assert df["break_z_induced_inches"].to_list() == [18.4, -9.8]


@pytest.mark.asyncio
async def test_savant_gamefeed_pitch_data_reads_row_level_pitcher_ids() -> None:
    payload = json.dumps(
        {
            "home_pitchers": [
                {
                    "pitcher_id": "111111",
                    "pitcher": {"id": 222222},
                    "player_id": 333333,
                    "pitcher_name": "Primary Id",
                },
                {
                    "pitcher": 444444,
                    "player": {"id": 555555},
                    "pitcher_name": "Pitcher Field",
                },
                {
                    "player_id": 666666,
                    "pitcher_name": "Player Id",
                },
                {
                    "pitcher": {"id": "777777"},
                    "pitcher_name": "Nested Pitcher",
                },
                {
                    "player": {"id": "888888"},
                    "pitcher_name": "Nested Player",
                },
            ],
            "away_pitchers": {},
        }
    )

    df = await savant_gamefeed_pitch_data(_GAME_PK, context=_context(payload))

    assert df["pitcher_id"].to_list() == [111111, 444444, 666666, 777777, 888888]


@pytest.mark.asyncio
async def test_savant_gamefeed_missing_nodes_return_typed_empty_dataframes() -> None:
    ctx = _context(json.dumps({}))

    exit_df = await savant_gamefeed_exit_velocity(_GAME_PK, context=ctx)
    pitch_df = await savant_gamefeed_pitch_data(_GAME_PK, context=ctx)

    assert exit_df.is_empty()
    assert pitch_df.is_empty()
    assert exit_df.schema["game_pk"] == pl.Int64
    assert pitch_df.schema["pitcher_id"] == pl.Int64
    assert pitch_df.schema["break_z_induced_inches"] == pl.Float64


@pytest.mark.asyncio
async def test_savant_gamefeed_invalid_json_fails_fast() -> None:
    with pytest.raises(UpstreamParseError, match="valid JSON"):
        await savant_gamefeed_exit_velocity(_GAME_PK, context=_context("not json"))


_GAME_PK_2 = 777002


def _gamefeed_payload_second() -> str:
    return json.dumps(
        {
            "exit_velocity": [
                {
                    "batter_name": "Judge Aaron",
                    "team_batting": "NYY",
                    "pitcher_name": "Cole Gerrit",
                    "team_fielding": "NYY",
                    "events": "Single",
                    "launch_speed": 112.4,
                    "launch_angle": 12,
                    "hit_distance": 310,
                    "xba": 0.580,
                    "start_speed": 96.8,
                    "contextMetrics": {"homeRunBallparks": 5},
                }
            ],
            "home_pitchers": {
                "543037": [
                    {
                        "pitcher_name": "Cole Gerrit",
                        "team_pitching": "NYY",
                        "batter_name": "Judge Aaron",
                        "team_batting": "NYY",
                        "pitch_name": "Sweeper",
                        "pitch_type": "SW",
                        "description": "Foul",
                        "events": "",
                        "start_speed": 96.8,
                        "spin_rate": 2560,
                        "breakXInches": -9.3,
                        "breakZInducedInches": 12.1,
                    }
                ]
            },
            "away_pitchers": {},
        }
    )


def _context_side_effect(payloads: Sequence[str]) -> BaseballContext:
    mock_cache = MagicMock()
    mock_cache.get.return_value = None

    async def _gof(key: str, fetcher: object, **kwargs: object) -> pl.DataFrame:
        return await fetcher()  # type: ignore[misc]

    mock_cache.get_or_fetch = AsyncMock(side_effect=_gof)
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text.side_effect = payloads
    return BaseballContext(http=mock_http, cache=mock_cache)


@pytest.mark.asyncio
async def test_savant_gamefeed_many_concatenates_multiple_games() -> None:
    payloads = [_gamefeed_payload(), _gamefeed_payload_second()]
    ev_ctx = _context_side_effect(payloads)
    pitch_ctx = _context_side_effect(payloads)

    ev_df = await savant_gamefeed_exit_velocity_many([_GAME_PK, _GAME_PK_2], context=ev_ctx)
    pitch_df = await savant_gamefeed_pitch_data_many([_GAME_PK, _GAME_PK_2], context=pitch_ctx)

    assert ev_df.height == 2
    assert ev_df["game_pk"].to_list() == [777001, 777002]
    assert ev_df["batter_name"].to_list() == ["Ohtani Shohei", "Judge Aaron"]
    assert pitch_df.height == 3
    assert pitch_df["game_pk"].to_list() == [777001, 777001, 777002]
    assert pitch_df["pitcher_id"].to_list() == [675916, 607192, 543037]


@pytest.mark.asyncio
async def test_savant_gamefeed_many_empty_input_returns_empty_df() -> None:
    ev_df = await savant_gamefeed_exit_velocity_many([], context=_context(_gamefeed_payload()))
    pitch_df = await savant_gamefeed_pitch_data_many([], context=_context(_gamefeed_payload()))

    assert ev_df.is_empty()
    assert ev_df.schema == pl.Schema(EXIT_VELOCITY_SCHEMA)
    assert pitch_df.is_empty()
    assert pitch_df.schema == pl.Schema(PITCH_DATA_SCHEMA)


@pytest.mark.asyncio
async def test_savant_gamefeed_many_single_game_equals_single_api() -> None:
    payload = _gamefeed_payload()
    single_ctx = _context(payload)
    many_ctx = _context(payload)

    single_df = await savant_gamefeed_exit_velocity(_GAME_PK, context=single_ctx)
    many_df = await savant_gamefeed_exit_velocity_many([_GAME_PK], context=many_ctx)

    assert single_df.equals(many_df)


@pytest.mark.asyncio
async def test_savant_gamefeed_many_invalid_game_pk_raises_error() -> None:
    with pytest.raises(InvalidParameterError):
        await savant_gamefeed_exit_velocity_many([_GAME_PK, "not-a-number"], context=_context(_gamefeed_payload()))


@pytest.mark.asyncio
async def test_savant_gamefeed_many_mixed_valid_invalid_fails_fast() -> None:
    with pytest.raises(InvalidParameterError, match="game_pk"):
        await savant_gamefeed_pitch_data_many([_GAME_PK, "bad", _GAME_PK_2], context=_context(_gamefeed_payload()))


def test_savant_gamefeed_nan_parsing() -> None:
    from polars_baseball.parsers.savant_gamefeed import _float_or_none, _int_or_none

    assert _float_or_none("NaN") is None
    assert _float_or_none("nan") is None
    assert _float_or_none("N/A") is None
    assert _float_or_none("null") is None
    assert _float_or_none(float("nan")) is None

    assert _int_or_none("NaN") is None
    assert _int_or_none("nan") is None
    assert _int_or_none("N/A") is None
    assert _int_or_none("null") is None
    assert _int_or_none(float("nan")) is None
