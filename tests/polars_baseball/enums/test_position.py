import pytest

from polars_baseball.enums.position import norm_positions
from polars_baseball.exceptions import InvalidParameterError


def test_norm_positions_code() -> None:
    assert norm_positions("SS") == "SS"


def test_norm_positions_code_to_word() -> None:
    assert norm_positions("SS", to_word=True) == "shortstop"


def test_norm_positions_numeric_input() -> None:
    assert norm_positions(6) == "6"


def test_norm_positions_all_returns_empty() -> None:
    assert norm_positions("ALL") == ""


def test_norm_positions_invalid() -> None:
    with pytest.raises(InvalidParameterError, match="not a valid position"):
        norm_positions("ZZ")


def test_norm_positions_of_returns_code() -> None:
    assert norm_positions("OF") == "OF"
