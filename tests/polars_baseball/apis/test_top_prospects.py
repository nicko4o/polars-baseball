import html
import json
from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest

from polars_baseball._client import HttpClient
from polars_baseball.apis.top_prospects import prospect_rankings, top_prospects
from polars_baseball.context import BaseballContext
from polars_baseball.exceptions import InvalidParameterError, UpstreamParseError

_MOCK_PROSPECT_HTML = (
    "<html><body>"
    "<table>"
    "<thead><tr><th>Rk</th><th>Player</th><th>Tm</th><th>Pos</th></tr></thead>"
    "<tbody>"
    "<tr><td>1</td><td>Adley Rutschman</td><td>BAL</td><td>C</td></tr>"
    "<tr><td>2</td><td>Bobby Witt Jr.</td><td>KC</td><td>SS</td></tr>"
    "</tbody>"
    "</table>"
    "</body></html>"
)


@pytest.mark.asyncio
@patch("polars_baseball.apis.top_prospects.default_context")
async def test_top_prospects_basic(mock_default_ctx: MagicMock) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=_MOCK_PROSPECT_HTML)
    mock_default_ctx.return_value = BaseballContext(http=mock_http)

    df = await top_prospects()
    assert isinstance(df, pl.DataFrame)
    assert df.height == 2
    assert "Player" in df.columns
    # Check that "Tm" column was dropped by postprocess
    assert "Tm" not in df.columns
    assert df["Player"][0] == "Adley Rutschman"


@pytest.mark.asyncio
@patch("polars_baseball.apis.top_prospects.resolve_team_id")
@patch("polars_baseball.apis.top_prospects.default_context")
async def test_top_prospects_team(
    mock_default_ctx: MagicMock,
    mock_resolve_team_id: AsyncMock,
) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=_MOCK_PROSPECT_HTML)
    mock_default_ctx.return_value = BaseballContext(http=mock_http)
    mock_resolve_team_id.return_value = 147

    df = await top_prospects(team_name="Yankees", player_type="batters")
    assert isinstance(df, pl.DataFrame)
    assert df.height == 2
    assert df["Player"][1] == "Bobby Witt Jr."


@pytest.mark.asyncio
async def test_top_prospects_rejects_invalid_player_type() -> None:
    with pytest.raises(InvalidParameterError, match="player_type"):
        await top_prospects(player_type="catchers")


@pytest.mark.asyncio
async def test_top_prospects_empty_response_fails_fast() -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value="")
    ctx = BaseballContext(http=mock_http)

    with pytest.raises(UpstreamParseError, match="empty"):
        await top_prospects(context=ctx)


@pytest.mark.asyncio
async def test_top_prospects_missing_tables_fails_fast() -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value="<html><body>No tables</body></html>")
    ctx = BaseballContext(http=mock_http)

    with pytest.raises(UpstreamParseError, match="tables"):
        await top_prospects(context=ctx)


@pytest.mark.asyncio
@patch("polars_baseball.apis.top_prospects.default_context")
async def test_prospect_rankings_basic(mock_default_ctx: MagicMock) -> None:
    mock_html = '<html><body><span data-init-state="{}"></span></body></html>'.format(
        html.escape(
            json.dumps(
                {
                    "payload": {
                        "ROOT_QUERY": {'getPlayerRankingsFromSelection({"limit":100,"slug":"sel-pr-2026-top100"})': []}
                    }
                }
            )
        )
    )

    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=mock_html)
    mock_default_ctx.return_value = BaseballContext(http=mock_http)

    df = await prospect_rankings()
    assert isinstance(df, pl.DataFrame)
    mock_http.get_text.assert_called_once_with("https://www.mlb.com/milb/prospects")


@pytest.mark.asyncio
@patch("polars_baseball.apis.top_prospects.default_context")
async def test_prospect_rankings_with_year_and_type(mock_default_ctx: MagicMock) -> None:
    mock_html = '<html><body><span data-init-state="{}"></span></body></html>'.format(
        html.escape(
            json.dumps(
                {
                    "payload": {
                        "ROOT_QUERY": {'getPlayerRankingsFromSelection({"limit":10,"slug":"sel-pr-2025-rhp"})': []}
                    }
                }
            )
        )
    )

    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=mock_html)
    mock_default_ctx.return_value = BaseballContext(http=mock_http)

    df = await prospect_rankings(list_type="rhp", year=2025)
    assert isinstance(df, pl.DataFrame)
    mock_http.get_text.assert_called_once_with("https://www.mlb.com/milb/prospects/2025/rhp")


@pytest.mark.asyncio
async def test_prospect_rankings_invalid_year() -> None:
    from polars_baseball._config import PROSPECT_RANKINGS_START_YEAR

    with pytest.raises(InvalidParameterError, match=f"Year must be between {PROSPECT_RANKINGS_START_YEAR}"):
        await prospect_rankings(year=PROSPECT_RANKINGS_START_YEAR - 1)
    with pytest.raises(InvalidParameterError, match="Year must be between"):
        await prospect_rankings(year=2100)


@pytest.mark.asyncio
async def test_prospect_rankings_empty_response() -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value="")
    ctx = BaseballContext(http=mock_http)

    with pytest.raises(UpstreamParseError, match="empty response"):
        await prospect_rankings(context=ctx)


@pytest.mark.asyncio
async def test_top_prospects_pitchers_missing_table_raises() -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=_MOCK_PROSPECT_HTML)
    ctx = BaseballContext(http=mock_http)
    with pytest.raises(UpstreamParseError, match="pitchers table"):
        await top_prospects(player_type="pitchers", context=ctx)


@pytest.mark.asyncio
@patch("polars_baseball._season.most_recent_season", return_value=2028)
async def test_prospect_rankings_dynamic_max_year(_mock_season: MagicMock) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value="")
    ctx = BaseballContext(http=mock_http)
    with pytest.raises(UpstreamParseError):
        await prospect_rankings(year=2032, context=ctx)
    with pytest.raises(InvalidParameterError, match="Year must be between"):
        await prospect_rankings(year=2033, context=ctx)
