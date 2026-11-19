from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from polars_baseball._client import HttpClient


def test_http_client_extra_headers_getter_setter() -> None:
    client = HttpClient()
    # Default should be empty dict
    assert client.extra_headers == {}

    # Setter should accept and convert mapping to dict
    client.extra_headers = {"Cookie": "foo=bar"}
    assert client.extra_headers == {"Cookie": "foo=bar"}

    # None should reset to empty dict
    client.extra_headers = None
    assert client.extra_headers == {}


@pytest.mark.asyncio
async def test_extra_headers_passed_to_request() -> None:
    client = HttpClient(impersonate=None)
    client.extra_headers = {"X-Test-Global": "global_val"}

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "ok"
    mock_response.raise_for_status.return_value = None

    mock_session = MagicMock()
    mock_session.get = AsyncMock(return_value=mock_response)

    # 1. Test requests with no local headers
    with patch.object(client, "get_cffi_session", return_value=mock_session):
        await client.get_text("https://baseballsavant.mlb.com/api")

    mock_session.get.assert_called_once_with(
        "https://baseballsavant.mlb.com/api",
        params=None,
        headers={"X-Test-Global": "global_val"},
    )
    mock_session.get.reset_mock()

    # 2. Test requests with local headers merging and overriding
    with patch.object(client, "get_cffi_session", return_value=mock_session):
        await client.get_text(
            "https://baseballsavant.mlb.com/api",
            headers={"X-Test-Local": "local_val", "X-Test-Global": "overridden"},
        )

    mock_session.get.assert_called_once_with(
        "https://baseballsavant.mlb.com/api",
        params=None,
        headers={"X-Test-Global": "overridden", "X-Test-Local": "local_val"},
    )


@pytest.mark.asyncio
async def test_extra_headers_passed_to_cffi() -> None:
    client = HttpClient(impersonate=None)
    client.extra_headers = {"Cookie": "cf_clearance=yes"}

    mock_resp = MagicMock()
    mock_resp.text = "cffi_ok"
    mock_resp.raise_for_status.return_value = None

    mock_session = MagicMock()
    mock_session.get = AsyncMock(return_value=mock_resp)

    # 1. Test requests with no local headers
    with patch.object(client, "get_cffi_session", return_value=mock_session):
        await client.get_text("https://www.fangraphs.com/leaders")

    mock_session.get.assert_called_once_with(
        "https://www.fangraphs.com/leaders",
        params=None,
        headers={"Cookie": "cf_clearance=yes"},
    )
    mock_session.get.reset_mock()

    # 2. Test requests with local headers merging and overriding
    with patch.object(client, "get_cffi_session", return_value=mock_session):
        await client.get_text(
            "https://www.fangraphs.com/leaders",
            headers={"Cookie": "cf_clearance=custom", "User-Agent": "test-agent"},
        )

    mock_session.get.assert_called_once_with(
        "https://www.fangraphs.com/leaders",
        params=None,
        headers={"Cookie": "cf_clearance=custom", "User-Agent": "test-agent"},
    )


@pytest.mark.asyncio
async def test_env_cf_clearance_scoped_to_cloudflare_origins_only(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("CF_COOKIE", raising=False)
    monkeypatch.setenv("CF_CLEARANCE", "secret_cf_token")

    client = HttpClient(impersonate=None)
    assert "Cookie" not in client.extra_headers

    mock_resp = MagicMock()
    mock_resp.text = "ok"
    mock_resp.raise_for_status.return_value = None

    mock_session = MagicMock()
    mock_session.get = AsyncMock(return_value=mock_resp)

    with patch.object(client, "get_cffi_session", return_value=mock_session):
        await client.get_text("https://www.baseball-reference.com/data")
        assert mock_session.get.call_args.kwargs["headers"] == {"Cookie": "cf_clearance=secret_cf_token"}
        mock_session.get.reset_mock()

        await client.get_text("https://www.fangraphs.com/leaders")
        assert mock_session.get.call_args.kwargs["headers"] == {"Cookie": "cf_clearance=secret_cf_token"}
        mock_session.get.reset_mock()

        for non_cf_url in (
            "https://statsapi.mlb.com/api/v1/schedule",
            "https://baseballsavant.mlb.com/api",
            "https://api.github.com/repos/chadwickbureau/retrosheet",
        ):
            await client.get_text(non_cf_url)
            sent_headers = mock_session.get.call_args.kwargs["headers"]
            assert sent_headers is None or "Cookie" not in sent_headers
            mock_session.get.reset_mock()


@pytest.mark.asyncio
async def test_extra_headers_cookie_not_leaked_to_non_cloudflare_origin() -> None:
    client = HttpClient(impersonate=None)
    client.extra_headers = {"Cookie": "cf_clearance=secret", "X-Custom": "ok"}

    mock_resp = MagicMock()
    mock_resp.text = "ok"
    mock_resp.raise_for_status.return_value = None

    mock_session = MagicMock()
    mock_session.get = AsyncMock(return_value=mock_resp)

    with patch.object(client, "get_cffi_session", return_value=mock_session):
        await client.get_text("https://statsapi.mlb.com/api/v1/schedule")
        assert mock_session.get.call_args.kwargs["headers"] == {"X-Custom": "ok"}
        mock_session.get.reset_mock()

        await client.get_text("https://www.fangraphs.com/leaders")
        assert mock_session.get.call_args.kwargs["headers"] == {"Cookie": "cf_clearance=secret", "X-Custom": "ok"}
        mock_session.get.reset_mock()

        # Per-request explicit headers remain honored (case-insensitively replacing Cookie)
        await client.get_text("https://www.fangraphs.com/leaders", headers={"cookie": "explicit=1"})
        assert mock_session.get.call_args.kwargs["headers"] == {"X-Custom": "ok", "cookie": "explicit=1"}
        mock_session.get.reset_mock()

        await client.get_text("https://statsapi.mlb.com/api/v1/schedule", headers={"Cookie": "explicit=1"})
        assert mock_session.get.call_args.kwargs["headers"] == {"X-Custom": "ok", "Cookie": "explicit=1"}
