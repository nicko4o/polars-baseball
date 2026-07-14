from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest

from polars_baseball._cache import GlobalCache
from polars_baseball._client import HttpClient
from polars_baseball.apis.bref import bwar_bat
from polars_baseball.context import BaseballContext
from polars_baseball.parsers.bref import BRefHTMLParser


def test_bref_html_parser_batting() -> None:
    html_content = """
    <html>
      <body>
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>Name</th>
              <th>G</th>
              <th>HR</th>
            </tr>
          </thead>
          <tbody>
            <tr>
              <td>1</td>
              <td><a href="/players/t/troutmi01.shtml?mlb_ID=545361">Mike Trout</a></td>
              <td>140</td>
              <td>45</td>
            </tr>
            <tr>
              <td>2</td>
              <td><a href="/players/j/judgeaa01.shtml?mlb_ID=592450">Aaron Judge</a></td>
              <td>150</td>
              <td>52</td>
            </tr>
          </tbody>
        </table>
      </body>
    </html>
    """

    df = BRefHTMLParser().parse(html_content)

    assert isinstance(df, pl.DataFrame)
    assert df.height == 2
    assert "mlbID" in df.columns
    assert df["mlbID"].to_list() == ["545361", "592450"]
    assert df["Name"].to_list() == ["Mike Trout", "Aaron Judge"]
    assert df["G"].to_list() == [140, 150]
    assert df["HR"].to_list() == [45, 52]


@pytest.mark.asyncio
@patch.object(GlobalCache, "set")
@patch.object(GlobalCache, "get", return_value=None)
@patch("polars_baseball.apis.bref.default_context")
async def test_bref_bwar_bat_api(
    mock_default_ctx: MagicMock,
    mock_cache_get: MagicMock,
    mock_cache_set: MagicMock,
) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(
        return_value="name_common,mlb_ID,player_ID,year_ID,team_ID,WAR\nMike Trout,545361,troutmi01,2026,LAA,8.5\n"
    )
    mock_default_ctx.return_value = BaseballContext(http=mock_http)

    df = await bwar_bat(return_all=False)

    assert isinstance(df, pl.DataFrame)
    assert df.height == 1
    assert df["name_common"][0] == "Mike Trout"
    assert df["WAR"][0] == 8.5
    assert "player_ID" in df.columns

    mock_http.get_text.assert_called_once()
    assert mock_cache_get.call_count == 2
    mock_cache_set.assert_called_once()


def test_bref_null_token_normalization() -> None:
    html = """
    <html><body>
    <table id="players_standard_batting">
      <thead>
        <tr><th>Game</th><th>Name</th><th>HR</th></tr>
      </thead>
      <tbody>
        <tr><td>1</td><td>---</td><td>---%</td></tr>
        <tr><td>2</td><td>nan</td><td>None</td></tr>
        <tr><td>3</td><td>none</td><td>null</td></tr>
        <tr><td>4</td><td></td><td>10</td></tr>
        <tr><td>summary</td><td>Total</td><td>10</td></tr>
      </tbody>
    </table>
    </body></html>
    """
    from polars_baseball.parsers.bref import BRefGameLogParser

    parser = BRefGameLogParser("batting")
    df = parser.parse(html)
    assert df["Name"].to_list() == [None, None, None, None]
    assert df["HR"].to_list() == [None, None, None, 10]
