import json
from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest

from polars_baseball import fangraphs as fg
from polars_baseball._cache import GlobalCache
from polars_baseball._client import HttpClient
from polars_baseball.apis.fangraphs import (
    FanGraphsFilter,
    FanGraphsFilterOp,
    FanGraphsRequest,
    _serialize_filters,
    fg_data,
)
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
                                            "HR": 45,
                                            "WAR": 8.5,
                                            "OPS": 1.083,
                                        },
                                        {
                                            "Name": '<a href="/playerprofile.aspx?playerid=15640">Aaron Judge</a>',
                                            "Team": "NYY",
                                            "playerid": 15640,
                                            "Season": 2019,
                                            "G": 102,
                                            "HR": 27,
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


@pytest.mark.asyncio
@patch.object(GlobalCache, "set")
@patch.object(GlobalCache, "get", return_value=None)
async def test_fangraphs_team_starters_wrapper(
    mock_cache_get: MagicMock,
    mock_cache_set: MagicMock,
) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=_make_mock_fg_html())
    ctx = BaseballContext(http=mock_http)

    df = await fg.team_starters(start_season=2024, team="NYY", context=ctx)

    assert df.height == 2
    mock_http.get_text.assert_called_once()
    _, kwargs = mock_http.get_text.call_args
    assert kwargs["params"]["stats"] == "sta"
    assert kwargs["params"]["team"] == "NYY,ts"
    assert mock_cache_get.call_count == 2
    mock_cache_set.assert_called_once()


@pytest.mark.asyncio
@patch.object(GlobalCache, "set")
@patch.object(GlobalCache, "get", return_value=None)
async def test_fangraphs_team_relievers_wrapper(
    mock_cache_get: MagicMock,
    mock_cache_set: MagicMock,
) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=_make_mock_fg_html())
    ctx = BaseballContext(http=mock_http)

    df = await fg.team_relievers(start_season=2024, team="LAD", context=ctx)

    assert df.height == 2
    mock_http.get_text.assert_called_once()
    _, kwargs = mock_http.get_text.call_args
    assert kwargs["params"]["stats"] == "rel"
    assert kwargs["params"]["team"] == "LAD,ts"
    assert mock_cache_get.call_count == 2
    mock_cache_set.assert_called_once()


@pytest.mark.asyncio
@patch.object(GlobalCache, "set")
@patch.object(GlobalCache, "get", return_value=None)
async def test_fangraphs_team_wrapper_accepts_position(
    mock_cache_get: MagicMock,
    mock_cache_set: MagicMock,
) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=_make_mock_fg_html())
    ctx = BaseballContext(http=mock_http)

    df = await fg.team_batting(start_season=2024, position="1B", context=ctx)

    assert df.height == 2
    mock_http.get_text.assert_called_once()
    _, kwargs = mock_http.get_text.call_args
    assert kwargs["params"]["pos"] == "1b"
    assert mock_cache_get.call_count == 2
    mock_cache_set.assert_called_once()


@pytest.mark.asyncio
@patch.object(GlobalCache, "set")
@patch.object(GlobalCache, "get", return_value=None)
async def test_fangraphs_team_wrapper_accepts_stat_columns(
    mock_cache_get: MagicMock,
    mock_cache_set: MagicMock,
) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=_make_mock_fg_html())
    ctx = BaseballContext(http=mock_http)

    df = await fg.team_pitching(start_season=2024, stat_columns=["ERA", "FIP"], context=ctx)

    assert df.height == 2
    mock_http.get_text.assert_called_once()
    _, kwargs = mock_http.get_text.call_args
    assert kwargs["params"]["pos"] == "all"
    assert kwargs["params"]["type"] is not None
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
            FanGraphsRequest(start_season=2019, league=123)  # type: ignore[arg-type]

    def test_from_raw_invalid_string_raises_value_error(self) -> None:
        with pytest.raises(InvalidParameterError, match="Invalid value"):
            FanGraphsRequest.from_raw(start_season=2019, league="INVALID")

    def test_from_raw_unknown_kwargs_raises_type_error(self) -> None:
        with pytest.raises(TypeError):
            FanGraphsRequest.from_raw(start_season=2019, invalid_param="hello")  # type: ignore[call-arg]

    def test_batting_with_filters(self) -> None:
        request = FanGraphsRequest.batting(
            start_season=2024,
            filters=[FanGraphsFilter(column="HR", operator=FanGraphsFilterOp.GT, value=40)],
        )
        assert len(request.filters) == 1
        assert request.filters[0].column == "HR"
        assert request.filters[0].operator == FanGraphsFilterOp.GT
        assert request.filters[0].value == 40

    def test_from_raw_with_filters(self) -> None:
        request = FanGraphsRequest.from_raw(
            start_season=2024,
            filters=[
                FanGraphsFilter(column="AVG", operator="gt", value=0.300),
                FanGraphsFilter(column="HR", operator="gte", value=20),
            ],
        )
        assert len(request.filters) == 2

    def test_filters_defaults_to_empty_list(self) -> None:
        request = FanGraphsRequest.batting(start_season=2024)
        assert request.filters == []


class TestFanGraphsFilter:
    def test_filter_op_enum_values(self) -> None:
        assert FanGraphsFilterOp.GT.value == "gt"
        assert FanGraphsFilterOp.LT.value == "lt"
        assert FanGraphsFilterOp.GTE.value == "gte"
        assert FanGraphsFilterOp.LTE.value == "lte"
        assert FanGraphsFilterOp.EQ.value == "eq"
        assert FanGraphsFilterOp.NE.value == "ne"

    def test_filter_creation_with_math_symbols(self) -> None:
        assert FanGraphsFilter(column="HR", operator=">", value=40).operator == "gt"
        assert FanGraphsFilter(column="AVG", operator=">=", value=0.3).operator == "gte"
        assert FanGraphsFilter(column="ERA", operator="<", value=3.0).operator == "lt"
        assert FanGraphsFilter(column="WHIP", operator="<=", value=1.1).operator == "lte"
        assert FanGraphsFilter(column="Team", operator="==", value="NYY").operator == "eq"
        assert FanGraphsFilter(column="Team", operator="=", value="NYY").operator == "eq"
        assert FanGraphsFilter(column="Team", operator="!=", value="BOS").operator == "ne"

    def test_filter_factory_methods(self) -> None:
        assert FanGraphsFilter.gt("HR", 40) == FanGraphsFilter("HR", "gt", 40)
        assert FanGraphsFilter.gte("AVG", 0.3) == FanGraphsFilter("AVG", "gte", 0.3)
        assert FanGraphsFilter.lt("ERA", 3.0) == FanGraphsFilter("ERA", "lt", 3.0)
        assert FanGraphsFilter.lte("WHIP", 1.1) == FanGraphsFilter("WHIP", "lte", 1.1)
        assert FanGraphsFilter.eq("Team", "NYY") == FanGraphsFilter("Team", "eq", "NYY")
        assert FanGraphsFilter.ne("Team", "BOS") == FanGraphsFilter("Team", "ne", "BOS")

    def test_filter_tuple_coercion(self) -> None:
        f = FanGraphsFilter.coerce(("HR", ">", 40))
        assert f.column == "HR"
        assert f.operator == "gt"
        assert f.value == 40

    def test_filter_coerce_invalid_type_raises_error(self) -> None:
        with pytest.raises(TypeError, match="Expected FanGraphsFilter or 3-tuple"):
            FanGraphsFilter.coerce("invalid")  # type: ignore[arg-type]

    def test_invalid_operator_raises_error(self) -> None:
        with pytest.raises(InvalidParameterError, match="Invalid operator 'invalid'"):
            FanGraphsFilter(column="HR", operator="invalid", value=40)

    def test_direct_request_instantiation_coerces_strings(self) -> None:
        req = FanGraphsRequest(
            start_season=2024,
            stats_category="BATTING",
            league="AL",
            month="MAY",
            position="1B",
            filters=[("HR", ">", 40)],
        )
        assert req.stats_category == FangraphsStatsCategory.BATTING
        assert req.league == FangraphsLeague.AL
        assert req.month == FangraphsMonth.MAY
        assert req.position == FangraphsPositions.FIRST_BASE
        assert len(req.filters) == 1
        assert req.filters[0] == FanGraphsFilter("HR", "gt", 40)


class TestSerializeFilters:
    def test_single_filter(self) -> None:
        filters = [FanGraphsFilter(column="HR", operator=FanGraphsFilterOp.GT, value=40)]
        result = _serialize_filters(filters)
        assert result == "HR,gt,40"

    def test_multiple_filters_joined_by_pipe(self) -> None:
        filters = [
            FanGraphsFilter(column="AVG", operator=FanGraphsFilterOp.GT, value=0.300),
            FanGraphsFilter(column="HR", operator="gte", value=20),
        ]
        result = _serialize_filters(filters)
        assert result == "AVG,gt,0.3|HR,gte,20"

    def test_empty_filters(self) -> None:
        result = _serialize_filters([])
        assert result == ""

    def test_string_op_serialization(self) -> None:
        filters = [FanGraphsFilter(column="Team", operator="eq", value="NYY")]
        result = _serialize_filters(filters)
        assert result == "Team,eq,NYY"


class TestFanGraphsUrlWithFilters:
    @pytest.mark.asyncio
    @patch.object(GlobalCache, "set")
    @patch.object(GlobalCache, "get", return_value=None)
    async def test_filter_param_in_url(
        self,
        mock_cache_get: MagicMock,
        mock_cache_set: MagicMock,
    ) -> None:
        mock_http = AsyncMock(spec=HttpClient)
        mock_http.get_text = AsyncMock(return_value=_make_mock_fg_html())
        ctx = BaseballContext(http=mock_http)

        filters = [FanGraphsFilter(column="HR", operator=FanGraphsFilterOp.GT, value=40)]
        request = FanGraphsRequest.batting(start_season=2024, filters=filters)
        await fg_data(request, context=ctx)

        mock_http.get_text.assert_called_once()
        _, kwargs = mock_http.get_text.call_args
        assert kwargs["params"]["filter"] == "HR,gt,40"

    @pytest.mark.asyncio
    @patch.object(GlobalCache, "set")
    @patch.object(GlobalCache, "get", return_value=None)
    async def test_no_filter_param_when_empty(
        self,
        mock_cache_get: MagicMock,
        mock_cache_set: MagicMock,
    ) -> None:
        mock_http = AsyncMock(spec=HttpClient)
        mock_http.get_text = AsyncMock(return_value=_make_mock_fg_html())
        ctx = BaseballContext(http=mock_http)

        request = FanGraphsRequest.batting(start_season=2024)
        await fg_data(request, context=ctx)

        mock_http.get_text.assert_called_once()
        _, kwargs = mock_http.get_text.call_args
        assert kwargs["params"]["filter"] == ""


class TestConvenienceFunctionsWithFilters:
    @pytest.mark.asyncio
    @patch.object(GlobalCache, "set")
    @patch.object(GlobalCache, "get", return_value=None)
    async def test_batting_wrapper_passes_filters(
        self,
        mock_cache_get: MagicMock,
        mock_cache_set: MagicMock,
    ) -> None:
        mock_http = AsyncMock(spec=HttpClient)
        mock_http.get_text = AsyncMock(return_value=_make_mock_fg_html())
        ctx = BaseballContext(http=mock_http)

        filters = [FanGraphsFilter(column="HR", operator=FanGraphsFilterOp.GT, value=40)]
        df = await fg.batting(start_season=2024, filters=filters, context=ctx)

        assert df.height == 1
        assert df["Name"][0] == "Mike Trout"
        mock_http.get_text.assert_called_once()
        _, kwargs = mock_http.get_text.call_args
        assert kwargs["params"]["filter"] == "HR,gt,40"

    @pytest.mark.asyncio
    @patch.object(GlobalCache, "set")
    @patch.object(GlobalCache, "get", return_value=None)
    async def test_batting_filters_nonexistent_column_raises_error(
        self,
        mock_cache_get: MagicMock,
        mock_cache_set: MagicMock,
    ) -> None:
        mock_http = AsyncMock(spec=HttpClient)
        mock_http.get_text = AsyncMock(return_value=_make_mock_fg_html())
        ctx = BaseballContext(http=mock_http)

        filters = [FanGraphsFilter(column="INVALID_COL", operator=FanGraphsFilterOp.GT, value=40)]
        with pytest.raises(InvalidParameterError, match="Filter column 'INVALID_COL' not found"):
            await fg.batting(start_season=2024, filters=filters, context=ctx)

    @pytest.mark.asyncio
    @patch.object(GlobalCache, "set")
    @patch.object(GlobalCache, "get", return_value=None)
    async def test_batting_filters_multiple_criteria(
        self,
        mock_cache_get: MagicMock,
        mock_cache_set: MagicMock,
    ) -> None:
        mock_http = AsyncMock(spec=HttpClient)
        mock_http.get_text = AsyncMock(return_value=_make_mock_fg_html())
        ctx = BaseballContext(http=mock_http)

        filters = [
            FanGraphsFilter(column="HR", operator=">", value=20),
            FanGraphsFilter(column="Team", operator="==", value="NYY"),
        ]
        df = await fg.batting(start_season=2024, filters=filters, context=ctx)

        assert df.height == 1
        assert df["Name"][0] == "Aaron Judge"

    @pytest.mark.asyncio
    @patch.object(GlobalCache, "set")
    @patch.object(GlobalCache, "get", return_value=None)
    async def test_fg_data_empty_data_returns_empty_dataframe(
        self,
        mock_cache_get: MagicMock,
        mock_cache_set: MagicMock,
    ) -> None:
        empty_next_data = {
            "props": {
                "pageProps": {
                    "dehydratedState": {
                        "queries": [
                            {
                                "queryKey": ["leaders/major-league/data", {}],
                                "state": {"data": {"data": []}},
                            }
                        ]
                    }
                }
            }
        }
        empty_html = (
            f'<html><head><script id="__NEXT_DATA__" type="application/json">'
            f"{json.dumps(empty_next_data)}</script></head><body></body></html>"
        )
        mock_http = AsyncMock(spec=HttpClient)
        mock_http.get_text = AsyncMock(return_value=empty_html)
        ctx = BaseballContext(http=mock_http)

        df = await fg_data(FanGraphsRequest.batting(start_season=2019), context=ctx)
        assert isinstance(df, pl.DataFrame)
        assert df.is_empty()
