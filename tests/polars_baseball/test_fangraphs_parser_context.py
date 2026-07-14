import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from polars_baseball import FanGraphsRequest, fg_data
from polars_baseball._cache import GlobalCache
from polars_baseball._client import HttpClient
from polars_baseball.context import BaseballContext
from polars_baseball.exceptions import UpstreamParseError
from polars_baseball.parsers.fangraphs import FangraphsHTMLParser


def _next_data_html(queries: list[object]) -> str:
    next_data = {
        "props": {
            "pageProps": {
                "dehydratedState": {
                    "queries": queries,
                },
            },
        },
    }
    return f'<script id="__NEXT_DATA__" type="application/json">{json.dumps(next_data)}</script>'


def _fangraphs_query(rows: list[object]) -> dict[str, object]:
    return {
        "queryKey": ["leaders/major-league/data"],
        "state": {"data": {"data": rows}},
    }


def test_fangraphs_parser_raises_without_next_data() -> None:
    parser = FangraphsHTMLParser()

    with pytest.raises(UpstreamParseError, match="__NEXT_DATA__"):
        parser.parse("<html></html>")


def test_fangraphs_parser_raises_for_missing_target_query() -> None:
    parser = FangraphsHTMLParser()

    with pytest.raises(UpstreamParseError, match="query key"):
        parser.parse(_next_data_html([{"queryKey": ["other"], "state": {"data": {"data": []}}}]))


def test_fangraphs_parser_raises_for_empty_player_data() -> None:
    parser = FangraphsHTMLParser()

    with pytest.raises(UpstreamParseError, match="player data"):
        parser.parse(_next_data_html([_fangraphs_query([])]))


@pytest.mark.asyncio
@patch.object(GlobalCache, "set")
@patch.object(GlobalCache, "get", return_value=None)
@patch("polars_baseball.apis.fangraphs.default_context")
async def test_fg_data_uses_injected_context(
    mock_default_context: MagicMock,
    _mock_cache_get: MagicMock,
    _mock_cache_set: MagicMock,
) -> None:
    rows: list[object] = [{"Name": "<a>Mike Trout</a>", "playerid": 19755}]
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=_next_data_html([_fangraphs_query(rows)]))
    ctx = BaseballContext(http=mock_http)

    df = await fg_data(FanGraphsRequest.batting(start_season=2019), context=ctx)

    assert df.height == 1
    assert df["Name"][0] == "Mike Trout"
    mock_http.get_text.assert_awaited_once()
    mock_default_context.assert_not_called()


def test_fangraphs_parser_raises_on_invalid_queries_entry_type() -> None:
    """When a queries entry is not a JSON object, it should raise UpstreamParseError."""
    parser = FangraphsHTMLParser()
    corrupt_html = _next_data_html([None])

    with pytest.raises(UpstreamParseError, match="queries entries to be JSON objects"):
        parser.parse(corrupt_html)
