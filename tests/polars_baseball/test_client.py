import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest
from curl_cffi.requests.exceptions import HTTPError as CurlHTTPError

from polars_baseball._client import HttpClient
from polars_baseball.exceptions import PolarsBaseballHttpError, PolarsBaseballTransportError


@pytest.fixture
def client() -> HttpClient:
    return HttpClient()


@pytest.mark.asyncio
async def test_get_text_httpx_success(client: HttpClient) -> None:
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.text = "csv,data\n1,2"

    mock_httpx = MagicMock(spec=httpx.AsyncClient)
    mock_httpx.get = AsyncMock(return_value=mock_response)

    with patch.object(client, "_httpx_client", mock_httpx):
        result = await client.get_text("https://baseballsavant.mlb.com/api")

    assert result == "csv,data\n1,2"
    mock_httpx.get.assert_called_once_with("https://baseballsavant.mlb.com/api", params=None)


@pytest.mark.asyncio
async def test_get_text_httpx_http_error(client: HttpClient) -> None:
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 404
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        message="Not Found",
        request=MagicMock(),
        response=mock_response,
    )

    mock_httpx = MagicMock(spec=httpx.AsyncClient)
    mock_httpx.get = AsyncMock(return_value=mock_response)

    with patch.object(client, "_httpx_client", mock_httpx):
        with pytest.raises(PolarsBaseballHttpError) as exc_info:
            await client.get_text("https://baseballsavant.mlb.com/notfound")

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_get_text_with_params_and_headers(client: HttpClient) -> None:
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.text = "ok"

    mock_httpx = MagicMock(spec=httpx.AsyncClient)
    mock_httpx.get = AsyncMock(return_value=mock_response)

    with patch.object(client, "_httpx_client", mock_httpx):
        result = await client.get_text(
            "https://baseballsavant.mlb.com/data",
            params={"key": "val"},
            headers={"Authorization": "Bearer x"},
        )

    assert result == "ok"
    mock_httpx.get.assert_called_once_with(
        "https://baseballsavant.mlb.com/data",
        params={"key": "val"},
        headers={"Authorization": "Bearer x"},
    )


@pytest.mark.asyncio
async def test_get_bytes_success(client: HttpClient) -> None:
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.content = b"binary data"

    mock_httpx = MagicMock(spec=httpx.AsyncClient)
    mock_httpx.get = AsyncMock(return_value=mock_response)

    with patch.object(client, "_httpx_client", mock_httpx):
        result = await client.get_bytes("https://github.com/data")

    assert result == b"binary data"


@pytest.mark.asyncio
async def test_get_bytes_http_error(client: HttpClient) -> None:
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 500
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        message="Server Error",
        request=MagicMock(),
        response=mock_response,
    )

    mock_httpx = MagicMock(spec=httpx.AsyncClient)
    mock_httpx.get = AsyncMock(return_value=mock_response)

    with patch.object(client, "_httpx_client", mock_httpx):
        with pytest.raises(PolarsBaseballHttpError) as exc_info:
            await client.get_bytes("https://github.com/error")

    assert exc_info.value.status_code == 500


@pytest.mark.asyncio
async def test_get_bref_uses_cffi_and_rate_limiting() -> None:
    client = HttpClient(bref_requests_per_minute=600)

    mock_resp = MagicMock()
    mock_resp.text = "bref_result"
    mock_resp.raise_for_status.return_value = None

    mock_session = MagicMock()
    mock_session.get = AsyncMock(return_value=mock_resp)

    with patch.object(client, "_cffi_session", mock_session):
        start = time.time()
        tasks = [client.get_text("https://www.baseball-reference.com/data") for _ in range(3)]
        results = await asyncio.gather(*tasks)
        elapsed = time.time() - start

    assert results == ["bref_result", "bref_result", "bref_result"]
    assert mock_session.get.call_count == 3
    assert elapsed >= 0.19


@pytest.mark.asyncio
async def test_get_fangraphs_uses_cffi() -> None:
    client = HttpClient()

    mock_resp = MagicMock()
    mock_resp.text = "fg_result"
    mock_resp.raise_for_status.return_value = None

    mock_session = MagicMock()
    mock_session.get = AsyncMock(return_value=mock_resp)

    with patch.object(client, "_cffi_session", mock_session):
        result = await client.get_text("https://www.fangraphs.com/leaders")

    assert result == "fg_result"
    mock_session.get.assert_called_once()


@pytest.mark.asyncio
async def test_get_bref_http_error(client: HttpClient) -> None:
    mock_session = MagicMock()
    mock_session.get = AsyncMock(side_effect=CurlHTTPError("Not Found", response=MagicMock(status_code=404)))

    with patch.object(client, "_cffi_session", mock_session):
        with pytest.raises(PolarsBaseballHttpError) as exc_info:
            await client.get_text("https://www.baseball-reference.com/notfound")

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_get_fangraphs_http_error(client: HttpClient) -> None:
    mock_session = MagicMock()
    mock_session.get = AsyncMock(side_effect=CurlHTTPError("Not Found", response=MagicMock(status_code=404)))

    with patch.object(client, "_cffi_session", mock_session):
        with pytest.raises(PolarsBaseballHttpError) as exc_info:
            await client.get_text("https://www.fangraphs.com/notfound")

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_lazy_init_httpx(client: HttpClient) -> None:
    assert client._httpx_client is None
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = 200
    mock_resp.text = "ok"

    mock_httpx = MagicMock(spec=httpx.AsyncClient)
    mock_httpx.get = AsyncMock(return_value=mock_resp)

    with patch.object(client, "get_httpx_client", return_value=mock_httpx):
        result = await client.get_text("https://example.com")

    assert result == "ok"


@pytest.mark.asyncio
async def test_close_resets_clients(client: HttpClient) -> None:
    mock_httpx = MagicMock(spec=httpx.AsyncClient)
    mock_httpx.aclose = AsyncMock()
    mock_session = MagicMock()
    mock_session.close = AsyncMock()

    client._httpx_client = mock_httpx
    client._cffi_session = mock_session

    await client.close()

    mock_httpx.aclose.assert_awaited_once()
    mock_session.close.assert_awaited_once()
    assert client._httpx_client is None
    assert client._cffi_session is None


@pytest.mark.asyncio
async def test_close_idempotent(client: HttpClient) -> None:
    await client.close()
    await client.close()


@pytest.mark.asyncio
async def test_get_unknown_url_defaults_to_httpx(client: HttpClient) -> None:
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 200
    mock_response.text = "default"

    mock_httpx = MagicMock(spec=httpx.AsyncClient)
    mock_httpx.get = AsyncMock(return_value=mock_response)

    with patch.object(client, "_httpx_client", mock_httpx):
        result = await client.get_text("https://unknown.example.com")

    assert result == "default"
    mock_httpx.get.assert_called_once()


@pytest.mark.asyncio
async def test_get_text_httpx_connect_timeout(client: HttpClient) -> None:
    """Transport failures must not masquerade as HTTP status responses."""
    mock_httpx = MagicMock(spec=httpx.AsyncClient)
    mock_httpx.get = AsyncMock(side_effect=httpx.ConnectTimeout("Connect timeout"))

    with patch.object(client, "_httpx_client", mock_httpx):
        with pytest.raises(PolarsBaseballTransportError) as exc_info:
            await client.get_text("https://baseballsavant.mlb.com/api")
    assert "Network request failed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_text_cffi_http_status_error(client: HttpClient) -> None:
    """Curl/CFFI HTTP error (like 429) should be wrapped in PolarsBaseballHttpError with the correct status."""
    from curl_cffi.requests.exceptions import HTTPError as CurlHTTPError

    mock_response = MagicMock()
    mock_response.status_code = 429

    mock_session = MagicMock()
    mock_session.get = AsyncMock(side_effect=CurlHTTPError("Too Many Requests", response=mock_response))

    with patch.object(client, "_cffi_session", mock_session):
        with pytest.raises(PolarsBaseballHttpError) as exc_info:
            await client.get_text("https://www.fangraphs.com/leaders")
    assert exc_info.value.status_code == 429
    assert "FanGraphs HTTP request failed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_httpx_retries_transient_status_before_success() -> None:
    client = HttpClient(retry_backoff_base_seconds=0)

    error_response = MagicMock(spec=httpx.Response)
    error_response.status_code = 503
    error_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        message="Service Unavailable",
        request=MagicMock(),
        response=error_response,
    )
    success_response = MagicMock(spec=httpx.Response)
    success_response.status_code = 200
    success_response.text = "ok"

    mock_httpx = MagicMock(spec=httpx.AsyncClient)
    mock_httpx.get = AsyncMock(side_effect=[error_response, success_response])

    with patch.object(client, "_httpx_client", mock_httpx):
        result = await client.get_text("https://baseballsavant.mlb.com/api")

    assert result == "ok"
    assert mock_httpx.get.await_count == 2


@pytest.mark.asyncio
async def test_httpx_does_not_retry_non_transient_status() -> None:
    client = HttpClient(retry_backoff_base_seconds=0)
    mock_response = MagicMock(spec=httpx.Response)
    mock_response.status_code = 404
    mock_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        message="Not Found",
        request=MagicMock(),
        response=mock_response,
    )

    mock_httpx = MagicMock(spec=httpx.AsyncClient)
    mock_httpx.get = AsyncMock(return_value=mock_response)

    with patch.object(client, "_httpx_client", mock_httpx):
        with pytest.raises(PolarsBaseballHttpError) as exc_info:
            await client.get_text("https://baseballsavant.mlb.com/notfound")

    assert exc_info.value.status_code == 404
    assert mock_httpx.get.await_count == 1


@pytest.mark.asyncio
async def test_httpx_retries_request_error_before_success() -> None:
    client = HttpClient(retry_backoff_base_seconds=0)
    success_response = MagicMock(spec=httpx.Response)
    success_response.status_code = 200
    success_response.text = "ok"

    mock_httpx = MagicMock(spec=httpx.AsyncClient)
    mock_httpx.get = AsyncMock(side_effect=[httpx.ConnectTimeout("Connect timeout"), success_response])

    with patch.object(client, "_httpx_client", mock_httpx):
        result = await client.get_text("https://baseballsavant.mlb.com/api")

    assert result == "ok"
    assert mock_httpx.get.await_count == 2


@pytest.mark.asyncio
async def test_httpx_retry_exhaustion_raises_last_status() -> None:
    client = HttpClient(max_retries=1, retry_backoff_base_seconds=0)
    first_response = MagicMock(spec=httpx.Response)
    first_response.status_code = 503
    first_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        message="Service Unavailable",
        request=MagicMock(),
        response=first_response,
    )
    second_response = MagicMock(spec=httpx.Response)
    second_response.status_code = 504
    second_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        message="Gateway Timeout",
        request=MagicMock(),
        response=second_response,
    )

    mock_httpx = MagicMock(spec=httpx.AsyncClient)
    mock_httpx.get = AsyncMock(side_effect=[first_response, second_response])

    with patch.object(client, "_httpx_client", mock_httpx):
        with pytest.raises(PolarsBaseballHttpError) as exc_info:
            await client.get_text("https://baseballsavant.mlb.com/api")

    assert exc_info.value.status_code == 504
    assert mock_httpx.get.await_count == 2


@pytest.mark.asyncio
async def test_cffi_retries_transient_status_before_success() -> None:
    client = HttpClient(retry_backoff_base_seconds=0)
    transient_response = MagicMock(status_code=429)
    success_response = MagicMock()
    success_response.text = "ok"
    success_response.raise_for_status.return_value = None

    mock_session = MagicMock()
    mock_session.get = AsyncMock(
        side_effect=[
            CurlHTTPError("Too Many Requests", response=transient_response),
            success_response,
        ]
    )

    with patch.object(client, "_cffi_session", mock_session):
        result = await client.get_text("https://www.fangraphs.com/leaders")

    assert result == "ok"
    assert mock_session.get.await_count == 2
