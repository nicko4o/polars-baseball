import html
import json
from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest

from polars_baseball._client import HttpClient
from polars_baseball.client import BaseballClient
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
async def test_top_prospects_basic() -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=_MOCK_PROSPECT_HTML)
    client = BaseballClient(http=mock_http)

    df = await client.mlb.top_prospects()
    assert isinstance(df, pl.DataFrame)
    assert df.height == 2
    assert "Player" in df.columns
    # Check that "Tm" column was dropped by postprocess
    assert "Tm" not in df.columns
    assert df["Player"][0] == "Adley Rutschman"


@pytest.mark.asyncio
async def test_top_prospects_team() -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=_MOCK_PROSPECT_HTML)
    client = BaseballClient(http=mock_http)
    client.mlb.resolve_team_id = AsyncMock(return_value=147)  # type: ignore[method-assign]

    df = await client.mlb.top_prospects(team_name="Yankees", player_type="batters")
    assert isinstance(df, pl.DataFrame)
    assert df.height == 2
    assert df["Player"][1] == "Bobby Witt Jr."


@pytest.mark.asyncio
async def test_top_prospects_rejects_invalid_player_type() -> None:
    client = BaseballClient()
    with pytest.raises(InvalidParameterError, match="player_type"):
        await client.mlb.top_prospects(player_type="catchers")


@pytest.mark.asyncio
async def test_top_prospects_empty_response_fails_fast() -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value="")
    client = BaseballClient(http=mock_http)

    with pytest.raises(UpstreamParseError, match="empty"):
        await client.mlb.top_prospects()


@pytest.mark.asyncio
async def test_top_prospects_missing_tables_fails_fast() -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value="<html><body>No tables</body></html>")
    client = BaseballClient(http=mock_http)

    with pytest.raises(UpstreamParseError, match="tables"):
        await client.mlb.top_prospects()


@pytest.mark.asyncio
async def test_prospect_rankings_basic() -> None:
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
    client = BaseballClient(http=mock_http)

    df = await client.mlb.prospect_rankings()
    assert isinstance(df, pl.DataFrame)
    mock_http.get_text.assert_called_once_with("https://www.mlb.com/milb/prospects")


@pytest.mark.asyncio
async def test_prospect_rankings_with_year_and_type() -> None:
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
    client = BaseballClient(http=mock_http)

    df = await client.mlb.prospect_rankings(list_type="rhp", year=2025)
    assert isinstance(df, pl.DataFrame)
    mock_http.get_text.assert_called_once_with("https://www.mlb.com/milb/prospects/2025/rhp")


@pytest.mark.asyncio
async def test_prospect_rankings_invalid_year() -> None:
    from polars_baseball._config import PROSPECT_RANKINGS_START_YEAR

    client = BaseballClient()
    with pytest.raises(InvalidParameterError, match=f"Year must be between {PROSPECT_RANKINGS_START_YEAR}"):
        await client.mlb.prospect_rankings(year=PROSPECT_RANKINGS_START_YEAR - 1)
    with pytest.raises(InvalidParameterError, match="Year must be between"):
        await client.mlb.prospect_rankings(year=2100)


@pytest.mark.asyncio
async def test_prospect_rankings_empty_response() -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value="")
    client = BaseballClient(http=mock_http)

    with pytest.raises(UpstreamParseError, match="empty response"):
        await client.mlb.prospect_rankings()


@pytest.mark.asyncio
async def test_top_prospects_pitchers_missing_table_raises() -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=_MOCK_PROSPECT_HTML)
    client = BaseballClient(http=mock_http)
    with pytest.raises(UpstreamParseError, match="pitchers table"):
        await client.mlb.top_prospects(player_type="pitchers")


@pytest.mark.asyncio
@patch("polars_baseball.mlb.most_recent_season", return_value=2028)
async def test_prospect_rankings_dynamic_max_year(_mock_season: MagicMock) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value="")
    client = BaseballClient(http=mock_http)
    with pytest.raises(UpstreamParseError):
        await client.mlb.prospect_rankings(year=2032)
    with pytest.raises(InvalidParameterError, match="Year must be between"):
        await client.mlb.prospect_rankings(year=2033)
