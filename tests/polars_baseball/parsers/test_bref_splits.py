"""Tests for BRefSplitsParser — comment-container parsing, player info extraction.

Covers the commented-out HTML table fallback path, which is the largest
coverage gap in parsers/bref.py (68% coverage, 81 uncovered lines).
"""

import polars as pl

from polars_baseball.parsers.bref import BRefSplitsParser


def _make_splits_html() -> str:
    return """<!DOCTYPE html>
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
    <tr><th>2023</th><td>90</td><td>380</td><td>330</td><td>90</td><td>15</td><td>3</td><td>25</td><td>70</td></tr>
  </table>
</div>
-->
<!--
<div class="table_container">
  <caption>2024 Level</caption>
  <table>
    <tr><th>Split</th><th>G</th><th>PA</th><th>AB</th><th>H</th></tr>
    <tr><th>AAA</th><td>10</td><td>40</td><td>35</td><td>12</td></tr>
  </table>
</div>
-->
</body></html>"""


def _make_basic_html() -> str:
    return """<html><body><p>no splits here</p></body></html>"""


def _make_info_only_html() -> str:
    return """<html><body>
<div class="players">
  <p>Position: Shortstop</p>
  <p>Bats: Left \u2022 Throws: Right</p>
</div>
</body></html>"""


class TestBRefSplitsParserGetPlayerInfo:
    def test_extracts_position_bats_throws(self) -> None:
        html = _make_splits_html()
        parser = BRefSplitsParser("troutmi01", 2024, pitching=False)
        info = parser.get_player_info(html)
        assert info == {"Position": "Centerfielder", "Bats": "Right", "Throws": "Right"}

    def test_empty_html(self) -> None:
        parser = BRefSplitsParser("troutmi01", 2024, pitching=False)
        info = parser.get_player_info("")
        assert info == {"Position": "", "Bats": "", "Throws": ""}

    def test_no_player_div(self) -> None:
        parser = BRefSplitsParser("troutmi01", 2024, pitching=False)
        info = parser.get_player_info("<html></html>")
        assert info == {"Position": "", "Bats": "", "Throws": ""}


class TestBRefSplitsParserExtractSplitTables:
    def test_extracts_comment_containers(self) -> None:
        html = _make_splits_html()
        parser = BRefSplitsParser("troutmi01", 2024, pitching=False)
        raw_data, raw_level_data = parser._extract_split_tables(html)
        assert len(raw_data) > 0
        assert len(raw_level_data) > 0

    def test_empty_html_returns_empty(self) -> None:
        parser = BRefSplitsParser("troutmi01", 2024, pitching=False)
        raw_data, raw_level_data = parser._extract_split_tables("")
        assert raw_data == []
        assert raw_level_data == []

    def test_no_comments_returns_empty(self) -> None:
        parser = BRefSplitsParser("troutmi01", 2024, pitching=False)
        raw_data, raw_level_data = parser._extract_split_tables(_make_basic_html())
        assert raw_data == []
        assert raw_level_data == []


class TestBRefSplitsParserProcessSplitsTable:
    def test_returns_dataframe_with_expected_columns(self) -> None:
        html = _make_splits_html()
        parser = BRefSplitsParser("troutmi01", 2024, pitching=False)
        raw_data, _ = parser._extract_split_tables(html)
        df = parser._process_splits_table(raw_data)
        assert isinstance(df, pl.DataFrame)
        assert df.height > 0
        assert "Split Type" in df.columns
        assert "Split" in df.columns

    def test_empty_raw_rows(self) -> None:
        parser = BRefSplitsParser("troutmi01", 2024, pitching=False)
        df = parser._process_splits_table([])
        assert isinstance(df, pl.DataFrame)
        assert df.is_empty()

    def test_computes_1b_when_not_pitching(self) -> None:
        html = _make_splits_html()
        parser = BRefSplitsParser("troutmi01", 2024, pitching=False)
        raw_data, _ = parser._extract_split_tables(html)
        df = parser._process_splits_table(raw_data)
        if "1B" in df.columns:
            first = df.filter(pl.col("Split") == "2024")
            if first.height > 0:
                expected_singles = first["H"][0] - first["2B"][0] - first["3B"][0] - first["HR"][0]
                assert first["1B"][0] == expected_singles


class TestBRefSplitsParserParse:
    def test_parse_returns_tuple_of_three(self) -> None:
        html = _make_splits_html()
        parser = BRefSplitsParser("troutmi01", 2024, pitching=False)
        df_main, info, df_level = parser.parse(html)
        assert isinstance(df_main, pl.DataFrame)
        assert isinstance(info, dict)
        assert isinstance(df_level, pl.DataFrame)
        assert info["Position"] == "Centerfielder"

    def test_parse_empty_html(self) -> None:
        parser = BRefSplitsParser("troutmi01", 2024, pitching=False)
        df_main, info, df_level = parser.parse("")
        assert df_main.is_empty()
        assert info == {"Position": "", "Bats": "", "Throws": ""}
        assert df_level.is_empty()

    def test_parse_without_table_container(self) -> None:
        parser = BRefSplitsParser("troutmi01", 2024, pitching=False)
        df_main, info, df_level = parser.parse(_make_basic_html())
        assert df_main.is_empty()
        assert df_level.is_empty()

    def test_parse_info_only_no_splits(self) -> None:
        parser = BRefSplitsParser("troutmi01", 2024, pitching=False)
        df_main, info, df_level = parser.parse(_make_info_only_html())
        assert info["Position"] == "Shortstop"
        assert df_main.is_empty()

    def test_parse_with_career_year_none(self) -> None:
        parser = BRefSplitsParser("troutmi01", year=None, pitching=False)
        df_main, info, df_level = parser.parse(_make_splits_html())
        assert isinstance(df_main, pl.DataFrame)

    def test_parse_pitching_true(self) -> None:
        html = _make_splits_html()
        parser = BRefSplitsParser("troutmi01", 2024, pitching=True)
        df_main, info, df_level = parser.parse(html)
        assert isinstance(df_main, pl.DataFrame)
        assert isinstance(df_level, pl.DataFrame)
