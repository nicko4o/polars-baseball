import pytest

from polars_baseball.enums.pitch import norm_pitch_code
from polars_baseball.exceptions import InvalidParameterError


def test_norm_pitch_code_fastball() -> None:
    assert norm_pitch_code("FF") == "FF"


def test_norm_pitch_code_curveball_by_name() -> None:
    assert norm_pitch_code("CURVEBALL") == "CU"


def test_norm_pitch_code_to_word() -> None:
    assert norm_pitch_code("FF", to_word=True) == "4-Seamer"


def test_norm_pitch_code_invalid() -> None:
    with pytest.raises(InvalidParameterError, match="not a valid pitch"):
        norm_pitch_code("ZZ")


def test_norm_pitch_code_all_returns_code() -> None:
    assert norm_pitch_code("ALL") == "ALL"
