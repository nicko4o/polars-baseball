import polars as pl
import pytest
from lxml.etree import ParserError

import polars_baseball.parsers.bref_standard_strategy as bref_standard_strategy
from polars_baseball.parsers.bref_standard_strategy import BRefCSVExportStrategy


@pytest.fixture
def strategy() -> BRefCSVExportStrategy:
    return BRefCSVExportStrategy()


def test_extract_no_csv_indicators(strategy: BRefCSVExportStrategy) -> None:
    df = strategy.extract("<html><body>no csv here</body></html>")
    assert isinstance(df, pl.DataFrame)
    assert df.is_empty()


def test_extract_catches_parser_error(strategy: BRefCSVExportStrategy, monkeypatch: pytest.MonkeyPatch) -> None:
    def failing_html(*args: object, **kwargs: object) -> object:
        raise ParserError("bad HTML")

    monkeypatch.setattr(bref_standard_strategy.lxml.etree, "HTML", failing_html)

    df = strategy.extract("<bad>html</bad>")

    assert isinstance(df, pl.DataFrame)
    assert df.is_empty()


def test_extract_propagates_memory_error(strategy: BRefCSVExportStrategy, monkeypatch: pytest.MonkeyPatch) -> None:
    def failing_html(*args: object, **kwargs: object) -> object:
        raise MemoryError("OOM")

    monkeypatch.setattr(bref_standard_strategy.lxml.etree, "HTML", failing_html)

    with pytest.raises(MemoryError):
        strategy.extract("<bad>html</bad>")


def test_extract_propagates_os_error(strategy: BRefCSVExportStrategy, monkeypatch: pytest.MonkeyPatch) -> None:
    def failing_html(*args: object, **kwargs: object) -> object:
        raise OSError("disk full")

    monkeypatch.setattr(bref_standard_strategy.lxml.etree, "HTML", failing_html)

    with pytest.raises(OSError):
        strategy.extract("<bad>html</bad>")


def test_extract_from_csv_table_with_th_elements(strategy: BRefCSVExportStrategy) -> None:
    """_parse_csv_table must handle <th> headers, not just <td>."""
    html = """
    <html><body>
    <table id="csv_players_standard_batting">
        <tr><th>Name</th><th>G</th><th>AB</th></tr>
        <tr><td>Player A</td><td>100</td><td>400</td></tr>
    </table>
    </body></html>
    """
    df = strategy.extract(html)
    assert df.height == 1
    assert list(df.columns) == ["Name", "G", "AB"]
    assert df["Name"][0] == "Player A"


def test_extract_from_csv_table_with_comma_in_field(strategy: BRefCSVExportStrategy) -> None:
    """_parse_csv_table must CSV-escape fields containing commas."""
    html = """
    <html><body>
    <table id="csv_players_standard_batting">
        <tr><td>Name</td><td>Note</td></tr>
        <tr><td>Player A</td><td>Some, note</td></tr>
    </table>
    </body></html>
    """
    df = strategy.extract(html)
    assert df.height == 1
    assert df["Note"][0] == "Some, note"
