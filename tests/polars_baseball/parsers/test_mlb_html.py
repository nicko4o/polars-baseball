"""Tests for MLBApiParser declarative string output.

Verifies that the parser emits all columns as pl.String and does NOT
attempt heuristic int/float type inference. Type coercion is the
responsibility of the schema validation layer (validate_and_cast_schema),
not the parser itself.
"""

import polars as pl
import pytest

from polars_baseball.parsers.mlb import MLBApiParser

_TABLE_HTML = """\
<html><body>
<table>
  <thead><tr><th>Rk</th><th>Player</th><th>HR</th><th>BA</th></tr></thead>
  <tbody>
    <tr><td>1</td><td>Mike Trout</td><td>40</td><td>0.307</td></tr>
    <tr><td>2</td><td>Aaron Judge</td><td>62</td><td>0.311</td></tr>
  </tbody>
</table>
</body></html>
"""

_EMPTY_TABLE_HTML = """\
<html><body>
<table>
  <thead><tr><th>A</th><th>B</th></tr></thead>
  <tbody></tbody>
</table>
</body></html>
"""


@pytest.fixture
def parser() -> MLBApiParser:
    return MLBApiParser()


# ── All columns must be String ────────────────────────────────────────


def test_parse_tables_all_columns_are_string(parser: MLBApiParser) -> None:
    """MLBApiParser must not perform heuristic type inference.

    All columns in the returned DataFrame must be pl.String (or pl.Utf8).
    Type coercion belongs to the schema validation layer.
    """
    dfs = parser.parse_tables(_TABLE_HTML)
    assert len(dfs) == 1
    df = dfs[0]
    for col_name, dtype in df.schema.items():
        assert dtype == pl.String, (
            f"Column '{col_name}' is {dtype}, expected pl.String. "
            "MLBApiParser must not perform heuristic type inference."
        )


def test_parse_returns_correct_shape(parser: MLBApiParser) -> None:
    """parse() must return a DataFrame with expected row count."""
    df = parser.parse(_TABLE_HTML)
    assert df.height == 2
    assert set(df.columns) == {"Rk", "Player", "HR", "BA"}


def test_parse_preserves_raw_string_values(parser: MLBApiParser) -> None:
    """String values must be preserved as-is, not coerced."""
    dfs = parser.parse_tables(_TABLE_HTML)
    df = dfs[0]
    assert df["Rk"].to_list() == ["1", "2"]
    assert df["HR"].to_list() == ["40", "62"]
    assert df["BA"].to_list() == ["0.307", "0.311"]


def test_parse_empty_html_returns_empty_df(parser: MLBApiParser) -> None:
    """No tables in HTML must produce an empty DataFrame."""
    df = parser.parse("<html><body>no tables</body></html>")
    assert isinstance(df, pl.DataFrame)
    assert df.is_empty()


def test_parse_tables_empty_table_omitted(parser: MLBApiParser) -> None:
    """Tables with headers but no data rows must be filtered out."""
    dfs = parser.parse_tables(_EMPTY_TABLE_HTML)
    assert dfs == []


def test_parse_tables_multiple_tables(parser: MLBApiParser) -> None:
    """All non-empty tables in the HTML must be returned."""
    html = _TABLE_HTML + _TABLE_HTML
    dfs = parser.parse_tables(html)
    assert len(dfs) == 2
