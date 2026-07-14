"""Contract tests: parsers must implement the Parser protocol via instance parse()."""

import polars as pl
import pytest

from polars_baseball.exceptions import UpstreamParseError
from polars_baseball.parsers import Parser
from polars_baseball.parsers.bref import BRefHTMLParser
from polars_baseball.parsers.fangraphs import FangraphsHTMLParser
from polars_baseball.parsers.savant import SavantCSVParser


def test_all_parsers_implement_protocol() -> None:
    parsers: list[type[object]] = [BRefHTMLParser, SavantCSVParser, FangraphsHTMLParser]
    for cls in parsers:
        instance = cls()
        assert isinstance(instance, Parser), f"{cls.__name__} does not implement Parser protocol"


def test_parse_returns_dataframe() -> None:
    parsers: list[Parser] = [BRefHTMLParser(), SavantCSVParser()]
    for parser in parsers:
        df = parser.parse("")
        assert isinstance(df, pl.DataFrame), f"{type(parser).__name__}.parse() did not return DataFrame"


def test_fangraphs_parse_fails_fast_for_invalid_html() -> None:
    parser: Parser = FangraphsHTMLParser()

    with pytest.raises(UpstreamParseError):
        parser.parse("")


def test_static_to_dataframe_not_exposed() -> None:
    """Static to_dataframe() should not be callable — use instance parse() instead."""
    for cls in (BRefHTMLParser, SavantCSVParser, FangraphsHTMLParser):
        maybe_static = getattr(cls, "to_dataframe", None)
        if maybe_static is not None:
            with pytest.raises(TypeError):
                maybe_static("")


def test_savant_parse_handles_csv() -> None:
    csv_data = "pitcher,release_speed,pitch_type\n123456,95.5,FF\n789012,84.2,SL\n"
    df = SavantCSVParser().parse(csv_data)
    assert df.height == 2
    assert df["pitcher"].to_list() == [123456, 789012]


def test_bref_parse_handles_html() -> None:
    df = BRefHTMLParser().parse("<html><table></table></html>")
    assert isinstance(df, pl.DataFrame)


def test_validate_and_cast_schema_casting_failure() -> None:
    from polars_baseball._schema_utils import validate_and_cast_schema
    from polars_baseball.exceptions import InvalidSchemaError

    df = pl.DataFrame({"Year": ["not-an-int"], "Rnd": [1], "RdPck": [1], "Name": ["Trout"]})
    type_mapping: dict[str, pl.DataType | type[pl.DataType]] = {"Year": pl.Int64}

    with pytest.raises(InvalidSchemaError, match="Failed to cast DataFrame columns"):
        validate_and_cast_schema(df, required_cols=["Year"], type_mapping=type_mapping)
