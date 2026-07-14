from polars_baseball.parsers.bref import BRefHTMLParser
from polars_baseball.parsers.fangraphs import FangraphsHTMLParser
from polars_baseball.parsers.savant import SavantCSVParser


def test_parser_classes_are_importable_directly() -> None:
    assert BRefHTMLParser is not None
    assert SavantCSVParser is not None
    assert FangraphsHTMLParser is not None
