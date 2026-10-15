from unittest.mock import AsyncMock

import polars as pl
import pytest

from polars_baseball._client import HttpClient
from polars_baseball.client import BaseballClient
from polars_baseball.exceptions import InvalidParameterError
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
async def test_bref_bwar_bat_api() -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(
        return_value="name_common,mlb_ID,player_ID,year_ID,team_ID,WAR\nMike Trout,545361,troutmi01,2026,LAA,8.5\n"
    )
    client = BaseballClient(http=mock_http)

    df = await client.bref.bwar_bat(all_columns=False)

    assert isinstance(df, pl.DataFrame)
    assert df.height == 1
    assert df["name_common"][0] == "Mike Trout"
    assert df["WAR"][0] == 8.5
    assert "player_ID" in df.columns

    mock_http.get_text.assert_called_once()


@pytest.mark.asyncio
async def test_bwar_bat_all_columns() -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(
        return_value="name_common,mlb_ID,player_ID,year_ID,team_ID,WAR\nMike Trout,545361,troutmi01,2026,LAA,8.5\n"
    )
    client = BaseballClient(http=mock_http)

    df = await client.bref.bwar_bat(all_columns=True)
    assert "name_common" in df.columns
    assert "WAR" in df.columns


@pytest.mark.asyncio
async def test_bwar_pitch_all_columns() -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(
        return_value="name_common,mlb_ID,player_ID,year_ID,team_ID,WAR\nShohei Ohtani,660271,ohtansh01,2026,LAA,6.0\n"
    )
    client = BaseballClient(http=mock_http)

    df = await client.bref.bwar_pitch(all_columns=True)
    assert "name_common" in df.columns


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


@pytest.mark.asyncio
async def test_bref_game_logs_parameter_validation() -> None:
    client = BaseballClient()
    with pytest.raises(InvalidParameterError, match="player_id must not be empty"):
        await client.bref.game_logs("", 2024)

    with pytest.raises(InvalidParameterError, match="log_type must be either 'batting' or 'pitching'"):
        await client.bref.game_logs("troutmi01", 2024, log_type="fielding")  # type: ignore[arg-type]


@pytest.mark.asyncio
async def test_bref_splits_parameter_validation() -> None:
    client = BaseballClient()
    with pytest.raises(InvalidParameterError, match="player_id must not be empty"):
        await client.bref.splits("", 2024)


@pytest.mark.asyncio
async def test_bref_game_logs_success() -> None:
    html = """
    <html><body>
    <table id="players_standard_batting">
      <thead>
        <tr><th>Date</th><th>Opp</th><th>PA</th><th>AB</th><th>R</th><th>H</th></tr>
      </thead>
      <tbody>
        <tr><td>2024-04-01</td><td>OAK</td><td>4</td><td>4</td><td>1</td><td>2</td></tr>
        <tr><td>summary</td><td>Total</td><td>4</td><td>4</td><td>1</td><td>2</td></tr>
      </tbody>
    </table>
    </body></html>
    """
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=html)
    client = BaseballClient(http=mock_http)

    df = await client.bref.game_logs("troutmi01", 2024, "batting")
    assert isinstance(df, pl.DataFrame)
    assert df.height == 1
    assert "Date" in df.columns
    mock_http.get_text.assert_called_once()


@pytest.mark.asyncio
async def test_bref_splits_success() -> None:
    html = """<!DOCTYPE html>
    <html><body>
    <div class="players">
      <p>Position: Centerfielder</p>
      <p>Bats: Right \u2022 Throws: Right</p>
    </div>
    <!--
    <div class="table_container">
      <caption>2024 Splits vs. RHP</caption>
      <table>
        <tr><th>Split</th><th>G</th><th>PA</th><th>AB</th><th>H</th><th>2B</th><th>3B</th><th>HR</th><th>RBI</th></tr>
        <tr><th>2024</th><td>100</td><td>400</td><td>350</td><td>100</td><td>20</td><td>5</td><td>30</td><td>80</td></tr>
      </table>
    </div>
    -->
    </body></html>"""
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=html)
    client = BaseballClient(http=mock_http)

    tables = await client.bref.splits("troutmi01", 2024, pitching=False)
    assert isinstance(tables, list)
    assert len(tables) == 3
    df_main, df_info, df_level = tables
    assert isinstance(df_main, pl.DataFrame)
    assert df_main.height == 1
    assert isinstance(df_info, pl.DataFrame)
    assert df_info["Position"][0] == "Centerfielder"
    assert isinstance(df_level, pl.DataFrame)
    mock_http.get_text.assert_called_once()
