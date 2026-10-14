import pytest

from polars_baseball._http_policy import resolve_request_policy


@pytest.mark.parametrize(
    "url",
    [
        "https://www.baseball-reference.com.evil.example/data",
        "https://www.fangraphs.com.evil.example/leaders",
        "http://www.baseball-reference.com/data",
    ],
)
def test_provider_policy_rejects_different_origins(url: str) -> None:
    policy = resolve_request_policy(url)
    assert policy.provider_label == "HTTP"
    assert policy.rate_limited is False


def test_provider_policy_accepts_same_origin() -> None:
    bref_policy = resolve_request_policy("https://www.baseball-reference.com/data")
    assert bref_policy.provider_label == "BRef"
    assert bref_policy.rate_limited is True

    fg_policy = resolve_request_policy("https://www.fangraphs.com/leaders")
    assert fg_policy.provider_label == "FanGraphs"
    assert fg_policy.rate_limited is False
