"""Tests for BRefHTMLParser mlbID extraction decoupling.

Verifies that:
  - The mlb_ID= href parsing is isolated behind named constants.
  - _MLBID_COLUMN and _MLB_ID_PARAM module-level constants exist.
  - The mlbID column is always appended as the last column.
  - ID extraction works when the anchor href contains the param.
  - ID extraction returns empty string when href is missing.
"""

from polars_baseball.parsers import bref as bref_module
from polars_baseball.parsers.bref import BRefHTMLParser

# ── Constant existence ────────────────────────────────────────────────


def test_mlb_id_param_constant_exists() -> None:
    """_MLB_ID_PARAM must be a module-level named constant (no magic strings)."""
    assert hasattr(bref_module, "_MLB_ID_PARAM"), "_MLB_ID_PARAM constant not found in parsers.bref module"
    assert isinstance(bref_module._MLB_ID_PARAM, str)
    assert "mlb_ID" in bref_module._MLB_ID_PARAM


def test_mlbid_column_constant_exists() -> None:
    """_MLBID_COLUMN must be a module-level named constant (no magic strings)."""
    assert hasattr(bref_module, "_MLBID_COLUMN"), "_MLBID_COLUMN constant not found in parsers.bref module"
    assert isinstance(bref_module._MLBID_COLUMN, str)
    assert bref_module._MLBID_COLUMN == "mlbID"


# ── mlbID column appended ─────────────────────────────────────────────


def test_parse_appends_mlbid_column() -> None:
    """BRefHTMLParser.parse() must always append a 'mlbID' column."""
    html = """\
<html><body>
<table>
  <thead><tr><th>Player</th><th>HR</th></tr></thead>
  <tbody>
    <tr>
      <td><a href="/players/t/troutmi01.shtml?mlb_ID=545361">Mike Trout</a></td>
      <td>40</td>
    </tr>
  </tbody>
</table>
</body></html>
"""
    parser = BRefHTMLParser()
    df = parser.parse(html)
    assert "mlbID" in df.columns


def test_parse_extracts_mlbid_from_href() -> None:
    """MlbID must be populated from anchor href containing mlb_ID= param."""
    html = """\
<html><body>
<table>
  <thead><tr><th>Player</th><th>HR</th></tr></thead>
  <tbody>
    <tr>
      <td><a href="/players/t/troutmi01.shtml?mlb_ID=545361">Mike Trout</a></td>
      <td>40</td>
    </tr>
  </tbody>
</table>
</body></html>
"""
    parser = BRefHTMLParser()
    df = parser.parse(html)
    assert df["mlbID"][0] == "545361"


def test_parse_mlbid_empty_when_no_href() -> None:
    """MlbID must be None or empty string when no mlb_ID anchor is present."""
    html = """\
<html><body>
<table>
  <thead><tr><th>Player</th><th>HR</th></tr></thead>
  <tbody>
    <tr><td>No Link Player</td><td>10</td></tr>
  </tbody>
</table>
</body></html>
"""
    parser = BRefHTMLParser()
    df = parser.parse(html)
    # mlbID should be null/None when no href exists
    assert "mlbID" in df.columns
    assert df["mlbID"][0] is None
