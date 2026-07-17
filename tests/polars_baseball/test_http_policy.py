import pytest

from polars_baseball._http_policy import TransportKind, resolve_request_policy


@pytest.mark.parametrize(
    "url",
    [
        "https://www.baseball-reference.com.evil.example/data",
        "https://www.fangraphs.com.evil.example/leaders",
        "http://www.baseball-reference.com/data",
    ],
)
def test_provider_policy_rejects_different_origins(url: str) -> None:
    assert resolve_request_policy(url).transport is TransportKind.HTTPX


@pytest.mark.parametrize(
    "url",
    [
        "https://www.baseball-reference.com/data",
        "https://www.fangraphs.com/leaders",
    ],
)
def test_provider_policy_accepts_same_origin(url: str) -> None:
    assert resolve_request_policy(url).transport is TransportKind.BROWSER
