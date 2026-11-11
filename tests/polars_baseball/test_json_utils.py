import pytest

from polars_baseball._json_utils import child_mapping, expect_mapping, safe_child_dict, to_float, to_int, to_str
from polars_baseball.exceptions import UpstreamStructureChangedError


def test_expect_mapping() -> None:
    expect_mapping({"key": "val"}, "test")
    with pytest.raises(UpstreamStructureChangedError, match="Expected test to be a Mapping"):
        expect_mapping("not_a_map", "test")


def test_child_mapping() -> None:
    data = {"child": {"nested": 1}}
    assert child_mapping(data, "child", "label") == {"nested": 1}
    with pytest.raises(UpstreamStructureChangedError, match="Expected label to be a Mapping"):
        child_mapping({"child": "invalid"}, "child", "label")


def test_safe_child_dict() -> None:
    assert safe_child_dict(None, "foo") == {}
    assert safe_child_dict({}, "foo") == {}
    assert safe_child_dict({"foo": "str"}, "foo") == {}
    assert safe_child_dict({"foo": {"bar": 1}}, "foo") == {"bar": 1}


def test_to_int() -> None:
    assert to_int(None) is None
    assert to_int("") is None
    assert to_int(42) == 42
    assert to_int("42") == 42
    assert to_int("42.0") == 42
    assert to_int(True) is None
    assert to_int(False) is None
    assert to_int("invalid") is None


def test_to_float() -> None:
    assert to_float(None) is None
    assert to_float("") is None
    assert to_float(42) == 42.0
    assert to_float(42.5) == 42.5
    assert to_float("42.5") == 42.5
    assert to_float(True) is None
    assert to_float(False) is None
    assert to_float("invalid") is None


def test_to_str() -> None:
    assert to_str(None) is None
    assert to_str("") is None
    assert to_str("   ") is None
    assert to_str("hello") == "hello"
    assert to_str(123) == "123"
