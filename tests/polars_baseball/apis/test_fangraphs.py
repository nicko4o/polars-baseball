import json
from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest

from polars_baseball import FanGraphsRequest, fg_data
from polars_baseball import fangraphs as fg
from polars_baseball._cache import GlobalCache
from polars_baseball._client import HttpClient
from polars_baseball.context import BaseballContext
from polars_baseball.enums.fangraphs import (
    FangraphsLeague,
    FangraphsMonth,
    FangraphsPositions,
    FangraphsStatsCategory,
)
from polars_baseball.exceptions import InvalidParameterError


def _make_mock_fg_html() -> str:
    next_data = {
        "props": {
            "pageProps": {
                "dehydratedState": {
                    "queries": [
                        {
                            "queryKey": [
                                "leaders/major-league/data",
                                {"pos": "all", "stats": "bat", "qual": "y", "season": 2019},
                            ],
                            "state": {
                                "data": {
                                    "data": [
                                        {
                                            "Name": '<a href="/playerprofile.aspx?playerid=19755">Mike Trout</a>',
                                            "Team": "LAA",
                                            "playerid": 19755,
                                            "Season": 2019,
                                            "G": 134,
                                            "WAR": 8.5,
                                            "OPS": 1.083,
                                        },
                                        {
                                            "Name": '<a href="/playerprofile.aspx?playerid=15640">Aaron Judge</a>',
                                            "Team": "NYY",
                                            "playerid": 15640,
                                            "Season": 2019,
                                            "G": 102,
                                            "WAR": 5.2,
                                            "OPS": 0.921,
                                        },
                                    ]
                                }
                            },
                        }
                    ]
                }
            }
        }
    }
    json_str = json.dumps(next_data)
    return (
        f'<html><head><script id="__NEXT_DATA__" type="application/json">{json_str}</script></head><body></body></html>'
    )


@pytest.mark.asyncio
@patch.object(GlobalCache, "set")
@patch.object(GlobalCache, "get", return_value=None)
async def test_fg_data_with_batting_request(
    mock_cache_get: MagicMock,
    mock_cache_set: MagicMock,
) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=_make_mock_fg_html())
    ctx = BaseballContext(http=mock_http)

    request = FanGraphsRequest.batting(start_season=2019)
    df = await fg_data(request, context=ctx)

    assert isinstance(df, pl.DataFrame)
    assert df.height == 2
    assert df["Name"][0] == "Mike Trout"
    assert df["WAR"][0] == 8.5
    assert df["playerid"][0] == 19755

    mock_http.get_text.assert_called_once()
    assert mock_cache_get.call_count == 2
    mock_cache_set.assert_called_once()


@pytest.mark.asyncio
@patch.object(GlobalCache, "set")
@patch.object(GlobalCache, "get", return_value=None)
async def test_fangraphs_batting_wrapper(
    mock_cache_get: MagicMock,
    mock_cache_set: MagicMock,
) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=_make_mock_fg_html())
    ctx = BaseballContext(http=mock_http)

    df = await fg.batting(start_season=2019, league="AL", max_results=20, context=ctx)

    assert df.height == 2
    mock_http.get_text.assert_called_once()
    _, kwargs = mock_http.get_text.call_args
    assert kwargs["params"]["lg"] == "al"
    assert kwargs["params"]["pageitems"] == "20"
    assert mock_cache_get.call_count == 2
    mock_cache_set.assert_called_once()


@pytest.mark.asyncio
@patch.object(GlobalCache, "set")
@patch.object(GlobalCache, "get", return_value=None)
async def test_namespace_batting_wrapper(
    mock_cache_get: MagicMock,
    mock_cache_set: MagicMock,
) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=_make_mock_fg_html())
    ctx = BaseballContext(http=mock_http)

    df = await fg.batting(start_season=2019, context=ctx)

    assert df.height == 2
    mock_http.get_text.assert_called_once()
    assert mock_cache_get.call_count == 2
    mock_cache_set.assert_called_once()


class TestFanGraphsRequest:
    def test_batting_factory_sets_correct_category(self) -> None:
        request = FanGraphsRequest.batting(start_season=2019)
        assert request.start_season == 2019
        assert request.end_season == 2019
        assert request.stats_category == FangraphsStatsCategory.BATTING
        assert not request.is_team_data

    def test_pitching_factory(self) -> None:
        request = FanGraphsRequest.pitching(start_season=2020, league=FangraphsLeague.NL)
        assert request.stats_category == FangraphsStatsCategory.PITCHING
        assert request.league == FangraphsLeague.NL

    def test_fielding_factory(self) -> None:
        request = FanGraphsRequest.fielding(start_season=2021, position=FangraphsPositions.SHORT_STOP)
        assert request.stats_category == FangraphsStatsCategory.FIELDING
        assert request.position == FangraphsPositions.SHORT_STOP

    def test_team_batting_factory(self) -> None:
        request = FanGraphsRequest.team_batting(start_season=2019)
        assert request.stats_category == FangraphsStatsCategory.BATTING
        assert request.is_team_data

    def test_team_pitching_factory(self) -> None:
        request = FanGraphsRequest.team_pitching(start_season=2019)
        assert request.stats_category == FangraphsStatsCategory.PITCHING
        assert request.is_team_data

    def test_team_fielding_factory(self) -> None:
        request = FanGraphsRequest.team_fielding(start_season=2019)
        assert request.stats_category == FangraphsStatsCategory.FIELDING
        assert request.is_team_data

    def test_team_starters_factory(self) -> None:
        request = FanGraphsRequest.team_starters(start_season=2019)
        assert request.stats_category == FangraphsStatsCategory.STARTERS
        assert request.is_team_data

    def test_team_relievers_factory(self) -> None:
        request = FanGraphsRequest.team_relievers(start_season=2019)
        assert request.stats_category == FangraphsStatsCategory.RELIEVERS
        assert request.is_team_data

    def test_end_season_defaults_to_start_season(self) -> None:
        request = FanGraphsRequest.batting(start_season=2022)
        assert request.end_season == 2022

    def test_custom_end_season(self) -> None:
        request = FanGraphsRequest(start_season=2018, end_season=2022)
        assert request.end_season == 2022

    def test_from_raw_string_parsing(self) -> None:
        request = FanGraphsRequest.from_raw(start_season=2019, league="AL", position="1B", month="MAY")
        assert request.league == FangraphsLeague.AL
        assert request.position == FangraphsPositions.FIRST_BASE
        assert request.month == FangraphsMonth.MAY

    def test_enum_values_passed_through(self) -> None:
        request = FanGraphsRequest(
            start_season=2019,
            league=FangraphsLeague.NL,
            position=FangraphsPositions.PITCHER,
            month=FangraphsMonth.JUNE,
        )
        assert request.league == FangraphsLeague.NL
        assert request.position == FangraphsPositions.PITCHER
        assert request.month == FangraphsMonth.JUNE

    def test_direct_invalid_type_raises_type_error(self) -> None:
        with pytest.raises(TypeError, match="league must be a FangraphsLeague"):
            FanGraphsRequest(start_season=2019, league="AL")  # type: ignore[arg-type]

    def test_from_raw_invalid_string_raises_value_error(self) -> None:
        with pytest.raises(InvalidParameterError, match="Invalid value"):
            FanGraphsRequest.from_raw(start_season=2019, league="INVALID")

    def test_from_raw_unknown_kwargs_raises_type_error(self) -> None:
        with pytest.raises(TypeError):
            FanGraphsRequest.from_raw(start_season=2019, invalid_param="hello")  # type: ignore[call-arg]
