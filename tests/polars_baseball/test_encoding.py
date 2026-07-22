from polars_baseball._encoding import (
    ensure_bytes,
    ensure_str,
)


def test_ensure_str_with_str() -> None:
    assert ensure_str("hello") == "hello"


def test_ensure_str_with_bytes() -> None:
    assert ensure_str(b"hello") == "hello"


def test_ensure_str_with_empty() -> None:
    assert ensure_str("") == ""
    assert ensure_str(b"") == ""


def test_ensure_bytes_with_bytes() -> None:
    assert ensure_bytes(b"hello") == b"hello"


def test_ensure_bytes_with_str() -> None:
    assert ensure_bytes("hello") == b"hello"


def test_ensure_bytes_with_empty() -> None:
    assert ensure_bytes("") == b""
    assert ensure_bytes(b"") == b""


def test_ensure_str_latin1_fallback() -> None:
    latin1_bytes = b"Jos\xe9"
    assert ensure_str(latin1_bytes) == "José"
