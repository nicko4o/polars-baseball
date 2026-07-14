from unittest.mock import MagicMock

import pytest

import polars_baseball.gateways.savant as savant_gateway
from polars_baseball.exceptions import UpstreamParseError
from polars_baseball.gateways.savant import SavantGateway


@pytest.fixture
def gateway() -> SavantGateway:
    ctx = MagicMock()
    return SavantGateway(ctx)


def test_verify_error_response_no_error(gateway: SavantGateway) -> None:
    """When 'error' not in first 200 chars, return None."""
    gateway._verify_error_response("col_a,col_b\n1,2\n")


def test_verify_error_response_error_column(gateway: SavantGateway) -> None:
    """When CSV has 'error' column with data, raise UpstreamParseError with message."""
    with pytest.raises(UpstreamParseError, match="some error msg"):
        gateway._verify_error_response("error\nsome error msg\n")


def test_verify_error_response_non_csv_with_error(gateway: SavantGateway) -> None:
    """When text contains 'error' but is not parseable CSV, raise UpstreamParseError."""
    with pytest.raises(UpstreamParseError, match="failed with an error row"):
        gateway._verify_error_response("error " * 100)


def test_verify_error_response_no_error_column(gateway: SavantGateway) -> None:
    """When CSV has an 'error' column but no rows, raise UpstreamParseError."""
    with pytest.raises(UpstreamParseError, match="failed with an error row"):
        gateway._verify_error_response("error,foo\n")


def test_verify_error_response_propagates_memory_error(gateway: SavantGateway, monkeypatch: pytest.MonkeyPatch) -> None:
    """MemoryError must NOT be swallowed by _verify_error_response."""

    def failing_read_csv(*args: object, **kwargs: object) -> object:
        raise MemoryError("OOM")

    monkeypatch.setattr(savant_gateway.pl, "read_csv", failing_read_csv)

    with pytest.raises(MemoryError):
        gateway._verify_error_response("error\nsome error\n")


def test_verify_error_response_propagates_os_error(gateway: SavantGateway, monkeypatch: pytest.MonkeyPatch) -> None:
    """OSError must NOT be swallowed by _verify_error_response."""

    def failing_read_csv(*args: object, **kwargs: object) -> object:
        raise OSError("disk full")

    monkeypatch.setattr(savant_gateway.pl, "read_csv", failing_read_csv)

    with pytest.raises(OSError):
        gateway._verify_error_response("error\nsome error\n")
