from unittest.mock import AsyncMock, MagicMock, patch

import httpx
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
async def test_extra_headers_passed_to_httpx() -> None:
    client = HttpClient()
    client.extra_headers = {"X-Test-Global": "global_val"}

    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.text = "ok"

    mock_httpx = MagicMock(spec=httpx.AsyncClient)
    mock_httpx.get = AsyncMock(return_value=mock_response)

    # 1. Test requests with no local headers
    with patch.object(client, "_httpx_client", mock_httpx):
        await client.get_text("https://baseballsavant.mlb.com/api")

    mock_httpx.get.assert_called_once_with(
        "https://baseballsavant.mlb.com/api",
        params=None,
        headers={"X-Test-Global": "global_val"},
    )
    mock_httpx.get.reset_mock()

    # 2. Test requests with local headers merging and overriding
    with patch.object(client, "_httpx_client", mock_httpx):
        await client.get_text(
            "https://baseballsavant.mlb.com/api",
            headers={"X-Test-Local": "local_val", "X-Test-Global": "overridden"},
        )

    mock_httpx.get.assert_called_once_with(
        "https://baseballsavant.mlb.com/api",
        params=None,
        headers={"X-Test-Global": "overridden", "X-Test-Local": "local_val"},
    )


@pytest.mark.asyncio
async def test_extra_headers_passed_to_cffi() -> None:
    client = HttpClient()
    client.extra_headers = {"Cookie": "cf_clearance=yes"}

    mock_resp = MagicMock()
    mock_resp.text = "cffi_ok"
    mock_resp.raise_for_status.return_value = None

    mock_session = MagicMock()
    mock_session.get = AsyncMock(return_value=mock_resp)

    # 1. Test requests with no local headers
    with patch.object(client, "_cffi_session", mock_session):
        await client.get_text("https://www.fangraphs.com/leaders")

    mock_session.get.assert_called_once_with(
        "https://www.fangraphs.com/leaders",
        params=None,
        headers={"Cookie": "cf_clearance=yes"},
    )
    mock_session.get.reset_mock()

    # 2. Test requests with local headers merging and overriding
    with patch.object(client, "_cffi_session", mock_session):
        await client.get_text(
            "https://www.fangraphs.com/leaders",
            headers={"Cookie": "cf_clearance=custom", "User-Agent": "test-agent"},
        )

    mock_session.get.assert_called_once_with(
        "https://www.fangraphs.com/leaders",
        params=None,
        headers={"Cookie": "cf_clearance=custom", "User-Agent": "test-agent"},
    )
