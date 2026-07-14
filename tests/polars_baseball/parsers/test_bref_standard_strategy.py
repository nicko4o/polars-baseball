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
