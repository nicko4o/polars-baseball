import polars as pl
import pytest

from polars_baseball.exceptions import UpstreamParseError
from polars_baseball.parsers import Parser
from polars_baseball.parsers.savant import SavantCSVParser


def test_parser_to_dataframe_success() -> None:
    csv_data = "pitcher,release_speed,pitch_type\n123456,95.5,FF\n789012,84.2,SL\n"
    df = SavantCSVParser().parse(csv_data)

    assert isinstance(df, pl.DataFrame)
    assert df.height == 2
    assert df["pitcher"].to_list() == [123456, 789012]
    assert df["release_speed"].to_list() == [95.5, 84.2]
    assert df["pitch_type"].to_list() == ["FF", "SL"]


def test_parser_invalid_value_becomes_null() -> None:
    csv_data = "pitcher,release_speed,pitch_type\n123456,fast,FF\n"
    df = SavantCSVParser().parse(csv_data)

    assert df.height == 1
    assert df["pitcher"][0] == 123456
    assert df["release_speed"][0] is None
    assert df["pitch_type"][0] == "FF"


def test_parser_extra_fields_preserved() -> None:
    csv_data = "pitcher,release_speed,pitch_type,events,extra_field\n123456,95.5,FF,,hello\n"
    df = SavantCSVParser().parse(csv_data)

    assert isinstance(df, pl.DataFrame)
    assert df.height == 1
    assert df["pitcher"][0] == 123456
    assert df["events"][0] is None
    assert df["extra_field"][0] == "hello"


def test_parser_empty_csv() -> None:
    df = SavantCSVParser().parse("")
    assert isinstance(df, pl.DataFrame)
    assert df.is_empty()

    df2 = SavantCSVParser().parse("   ")
    assert isinstance(df2, pl.DataFrame)
    assert df2.is_empty()


def test_parser_string_stripping() -> None:
    csv_data = "pitcher,pitch_type\n123456,  FF  \n789012,  SL  \n"
    df = SavantCSVParser().parse(csv_data)

    assert df["pitch_type"].to_list() == ["FF", "SL"]


def test_parser_whitespace_columns() -> None:
    csv_data = "pitcher , release_speed ,pitch_type\n123456,95.5,FF\n"
    df = SavantCSVParser().parse(csv_data)

    assert "pitcher" in df.columns
    assert "release_speed" in df.columns
    assert "pitch_type" in df.columns


def test_parser_protocol_accepts_savant() -> None:
    parser: Parser = SavantCSVParser()
    csv_data = "pitcher,release_speed\n123456,95.5\n"
    df = parser.parse(csv_data)
    assert isinstance(df, pl.DataFrame)
    assert df.height == 1


def test_parser_protocol_accepts_bref() -> None:
    from polars_baseball.parsers.bref import BRefHTMLParser

    parser: Parser = BRefHTMLParser()
    df = parser.parse("<html><table></table></html>")
    assert isinstance(df, pl.DataFrame)


def test_fangraphs_parser_protocol() -> None:
    from polars_baseball.parsers.fangraphs import FangraphsHTMLParser

    parser: Parser = FangraphsHTMLParser()
    html = "<html><body></body></html>"
    with pytest.raises(UpstreamParseError):
        parser.parse(html)


def test_fangraphs_parser_extracts_data() -> None:
    import json

    from polars_baseball.parsers.fangraphs import FangraphsHTMLParser

    next_data = {
        "props": {
            "pageProps": {
                "dehydratedState": {
                    "queries": [
                        {
                            "queryKey": ["leaders/major-league/data", {}],
                            "state": {
                                "data": {
                                    "data": [
                                        {"Name": "Player A", "WAR": 5.0},
                                        {"Name": "Player B", "WAR": 3.2},
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
    html = f'<html><script id="__NEXT_DATA__" type="application/json">{json_str}</script></html>'

    parser = FangraphsHTMLParser()
    df = parser.parse(html)
    assert df.height == 2
    assert df["Name"].to_list() == ["Player A", "Player B"]
    assert df["WAR"].to_list() == [5.0, 3.2]


def test_fangraphs_parser_strips_html_tags() -> None:
    import json

    from polars_baseball.parsers.fangraphs import FangraphsHTMLParser

    next_data = {
        "props": {
            "pageProps": {
                "dehydratedState": {
                    "queries": [
                        {
                            "queryKey": ["leaders/major-league/data", {}],
                            "state": {
                                "data": {
                                    "data": [
                                        {"Name": '<a href="/player">Mike Trout</a>', "WAR": 8.5},
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
    html = f'<html><script id="__NEXT_DATA__" type="application/json">{json_str}</script></html>'

    parser = FangraphsHTMLParser()
    df = parser.parse(html)
    assert df["Name"][0] == "Mike Trout"


def test_bref_game_log_parser_coercion() -> None:
    from polars_baseball.parsers.bref import BRefGameLogParser

    html = """
    <html><body>
    <table id="players_standard_batting">
      <thead>
        <tr><th>Game</th><th>Basic_AB</th><th>Basic_OPS</th><th>Custom_Int</th><th>Custom_Float</th><th>Custom_Str</th></tr>
      </thead>
      <tbody>
        <tr><td>1</td><td>4</td><td>0.950</td><td>100</td><td>1.5</td><td>abc</td></tr>
        <tr><td>2</td><td>3</td><td>1.200</td><td>200</td><td>2.5</td><td>def</td></tr>
        <tr><td></td><td></td><td></td><td></td><td></td><td></td></tr>
      </tbody>
    </table>
    </body></html>
    """
    parser = BRefGameLogParser("batting")
    df = parser.parse(html)

    # Static match checks
    assert df["Game"].dtype == pl.Int64
    assert df["Basic_AB"].dtype == pl.Int64
    assert df["Basic_OPS"].dtype == pl.Float64

    # Dynamic fallback checks (unmapped fields remain String)
    assert df["Custom_Int"].dtype == pl.String
    assert df["Custom_Float"].dtype == pl.String
    assert df["Custom_Str"].dtype == pl.String


def test_bref_coercion_fail_fast() -> None:
    from polars_baseball.parsers.bref import BRefGameLogParser

    html = """
    <html><body>
    <table id="players_standard_batting">
      <thead>
        <tr><th>Game</th><th>Basic_AB</th></tr>
      </thead>
      <tbody>
        <tr><td>1</td><td>not_a_number</td></tr>
        <tr><td>2</td><td>100</td></tr>
      </tbody>
    </table>
    </body></html>
    """
    parser = BRefGameLogParser("batting")
    with pytest.raises(UpstreamParseError, match="failed strict cast"):
        parser.parse(html)
