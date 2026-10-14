import asyncio
import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from curl_cffi.requests.exceptions import HTTPError as CurlHTTPError, RequestException as CurlRequestException

from polars_baseball._client import HttpClient
from polars_baseball.exceptions import PolarsBaseballHttpError, PolarsBaseballTransportError


@pytest.fixture
def client() -> HttpClient:
    return HttpClient()


def test_http_client_accepts_explicit_timeout() -> None:
    client = HttpClient(timeout=3.5)

    with patch("polars_baseball._client.AsyncSession") as mock_session_class:
        client.get_cffi_session()

    mock_session_class.assert_called_once()
    assert mock_session_class.call_args.kwargs["timeout"] == 3.5


def test_http_client_rejects_non_positive_timeout() -> None:
    with pytest.raises(ValueError, match="timeout must be greater than 0"):
        HttpClient(timeout=0)


@pytest.mark.asyncio
async def test_get_text_success(client: HttpClient) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "csv,data\n1,2"
    mock_response.raise_for_status.return_value = None

    mock_session = MagicMock()
    mock_session.get = AsyncMock(return_value=mock_response)

    with patch.object(client, "_cffi_session", mock_session):
        result = await client.get_text("https://baseballsavant.mlb.com/api")

    assert result == "csv,data\n1,2"
    mock_session.get.assert_called_once_with(
        "https://baseballsavant.mlb.com/api",
        params=None,
        headers=None,
    )


@pytest.mark.asyncio
async def test_get_text_http_error(client: HttpClient) -> None:
    mock_session = MagicMock()
    mock_session.get = AsyncMock(side_effect=CurlHTTPError("Not Found", response=MagicMock(status_code=404)))

    with patch.object(client, "_cffi_session", mock_session):
        with pytest.raises(PolarsBaseballHttpError) as exc_info:
            await client.get_text("https://baseballsavant.mlb.com/notfound")

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
async def test_get_text_with_params_and_headers(client: HttpClient) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = "ok"
    mock_response.raise_for_status.return_value = None

    mock_session = MagicMock()
    mock_session.get = AsyncMock(return_value=mock_response)

    with patch.object(client, "_cffi_session", mock_session):
        result = await client.get_text(
            "https://baseballsavant.mlb.com/data",
            params={"key": "val"},
            headers={"Authorization": "Bearer x"},
        )

    assert result == "ok"
    mock_session.get.assert_called_once_with(
        "https://baseballsavant.mlb.com/data",
        params={"key": "val"},
        headers={"Authorization": "Bearer x"},
    )


@pytest.mark.asyncio
async def test_get_bytes_success(client: HttpClient) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.content = b"binary data"
    mock_response.raise_for_status.return_value = None

    mock_session = MagicMock()
    mock_session.get = AsyncMock(return_value=mock_response)

    with patch.object(client, "_cffi_session", mock_session):
        result = await client.get_bytes("https://github.com/data")

    assert result == b"binary data"


@pytest.mark.asyncio
async def test_get_bytes_http_error(client: HttpClient) -> None:
    mock_session = MagicMock()
    mock_session.get = AsyncMock(side_effect=CurlHTTPError("Server Error", response=MagicMock(status_code=500)))

    with patch.object(client, "_cffi_session", mock_session):
        with pytest.raises(PolarsBaseballHttpError) as exc_info:
            await client.get_bytes("https://github.com/error")

    assert exc_info.value.status_code == 500


@pytest.mark.asyncio
async def test_post_json_success(client: HttpClient) -> None:
    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.text = '{"status": "ok"}'
    mock_response.raise_for_status.return_value = None

    mock_session = MagicMock()
    mock_session.post = AsyncMock(return_value=mock_response)

    with patch.object(client, "_cffi_session", mock_session):
        result = await client.post_json("https://example.com/api", {"foo": "bar"})

    assert result == '{"status": "ok"}'
    mock_session.post.assert_called_once_with(
        "https://example.com/api",
        json={"foo": "bar"},
        headers=None,
    )


@pytest.mark.asyncio
async def test_post_json_http_error(client: HttpClient) -> None:
    mock_session = MagicMock()
    mock_session.post = AsyncMock(side_effect=CurlHTTPError("Forbidden", response=MagicMock(status_code=403)))

    with patch.object(client, "_cffi_session", mock_session):
        with pytest.raises(PolarsBaseballHttpError) as exc_info:
            await client.post_json("https://example.com/api", {"foo": "bar"})

    assert exc_info.value.status_code == 403


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
async def test_get_bref_does_not_rate_limit_by_default() -> None:
    client = HttpClient()
    mock_resp = MagicMock()
    mock_resp.text = "bref_result"
    mock_resp.raise_for_status.return_value = None
    mock_session = MagicMock()
    mock_session.get = AsyncMock(return_value=mock_resp)

    with (
        patch.object(client, "_cffi_session", mock_session),
        patch.object(client, "_rate_limit", AsyncMock()) as mock_rate_limit,
    ):
        result = await client.get_text("https://www.baseball-reference.com/data")

    assert result == "bref_result"
    mock_rate_limit.assert_not_awaited()


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
async def test_lazy_init_cffi(client: HttpClient) -> None:
    assert client._cffi_session is None
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = "ok"
    mock_resp.raise_for_status.return_value = None

    mock_session = MagicMock()
    mock_session.get = AsyncMock(return_value=mock_resp)

    with patch.object(client, "get_cffi_session", return_value=mock_session):
        result = await client.get_text("https://example.com")

    assert result == "ok"


@pytest.mark.asyncio
async def test_close_resets_session(client: HttpClient) -> None:
    mock_session = MagicMock()
    mock_session.close = AsyncMock()

    client._cffi_session = mock_session

    await client.close()

    mock_session.close.assert_awaited_once()
    assert client._cffi_session is None


@pytest.mark.asyncio
async def test_close_idempotent(client: HttpClient) -> None:
    await client.close()
    await client.close()


@pytest.mark.asyncio
async def test_get_text_connect_timeout(client: HttpClient) -> None:
    """Transport failures must not masquerade as HTTP status responses."""
    mock_session = MagicMock()
    mock_session.get = AsyncMock(side_effect=CurlRequestException("Connect timeout"))

    with patch.object(client, "_cffi_session", mock_session):
        with pytest.raises(PolarsBaseballTransportError) as exc_info:
            await client.get_text("https://baseballsavant.mlb.com/api")
    assert "network request failed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_get_text_cffi_http_status_error(client: HttpClient) -> None:
    """Curl/CFFI HTTP error (like 429) should be wrapped in PolarsBaseballHttpError with the correct status."""
    mock_response = MagicMock(status_code=429)

    mock_session = MagicMock()
    mock_session.get = AsyncMock(side_effect=CurlHTTPError("Too Many Requests", response=mock_response))

    with patch.object(client, "_cffi_session", mock_session):
        with pytest.raises(PolarsBaseballHttpError) as exc_info:
            await client.get_text("https://www.fangraphs.com/leaders")
    assert exc_info.value.status_code == 429
    assert "FanGraphs HTTP request failed" in str(exc_info.value)


@pytest.mark.asyncio
async def test_retries_transient_status_by_default() -> None:
    client = HttpClient(retry_backoff_base_seconds=0)

    error_response = MagicMock(status_code=503)

    mock_session = MagicMock()
    mock_session.get = AsyncMock(side_effect=CurlHTTPError("Service Unavailable", response=error_response))

    with patch.object(client, "_cffi_session", mock_session):
        with pytest.raises(PolarsBaseballHttpError) as exc_info:
            await client.get_text("https://baseballsavant.mlb.com/api")

    assert exc_info.value.status_code == 503
    assert mock_session.get.await_count == 3  # Initial + 2 retries (DEFAULT_MAX_RETRIES=2)


@pytest.mark.asyncio
async def test_does_not_retry_transient_status_when_max_retries_zero() -> None:
    client = HttpClient(max_retries=0, retry_backoff_base_seconds=0)

    error_response = MagicMock(status_code=503)

    mock_session = MagicMock()
    mock_session.get = AsyncMock(side_effect=CurlHTTPError("Service Unavailable", response=error_response))

    with patch.object(client, "_cffi_session", mock_session):
        with pytest.raises(PolarsBaseballHttpError) as exc_info:
            await client.get_text("https://baseballsavant.mlb.com/api")

    assert exc_info.value.status_code == 503
    assert mock_session.get.await_count == 1


@pytest.mark.asyncio
async def test_cffi_bref_403_includes_cloudflare_guidance() -> None:
    client = HttpClient()
    mock_session = MagicMock()
    mock_session.get = AsyncMock(side_effect=CurlHTTPError("Forbidden", response=MagicMock(status_code=403)))

    with patch.object(client, "_cffi_session", mock_session):
        with pytest.raises(PolarsBaseballHttpError) as exc_info:
            await client.get_text("https://www.baseball-reference.com/data/war_daily_bat.txt")

    assert exc_info.value.status_code == 403
    assert "Cloudflare Turnstile" in str(exc_info.value)
    assert "CF_CLEARANCE" in str(exc_info.value)


@pytest.mark.asyncio
async def test_retries_transient_status_before_success_when_configured() -> None:
    client = HttpClient(max_retries=1, retry_backoff_base_seconds=0)

    error_response = MagicMock(status_code=503)
    success_response = MagicMock()
    success_response.status_code = 200
    success_response.text = "ok"
    success_response.raise_for_status.return_value = None

    mock_session = MagicMock()
    mock_session.get = AsyncMock(
        side_effect=[
            CurlHTTPError("Service Unavailable", response=error_response),
            success_response,
        ]
    )

    with patch.object(client, "_cffi_session", mock_session):
        result = await client.get_text("https://baseballsavant.mlb.com/api")

    assert result == "ok"
    assert mock_session.get.await_count == 2


@pytest.mark.asyncio
async def test_does_not_retry_non_transient_status() -> None:
    client = HttpClient(retry_backoff_base_seconds=0)
    mock_response = MagicMock(status_code=404)

    mock_session = MagicMock()
    mock_session.get = AsyncMock(side_effect=CurlHTTPError("Not Found", response=mock_response))

    with patch.object(client, "_cffi_session", mock_session):
        with pytest.raises(PolarsBaseballHttpError) as exc_info:
            await client.get_text("https://baseballsavant.mlb.com/notfound")

    assert exc_info.value.status_code == 404
    assert mock_session.get.await_count == 1


@pytest.mark.asyncio
async def test_retries_request_error_before_success() -> None:
    client = HttpClient(max_retries=1, retry_backoff_base_seconds=0)
    success_response = MagicMock()
    success_response.status_code = 200
    success_response.text = "ok"
    success_response.raise_for_status.return_value = None

    mock_session = MagicMock()
    mock_session.get = AsyncMock(side_effect=[CurlRequestException("Connect timeout"), success_response])

    with patch.object(client, "_cffi_session", mock_session):
        result = await client.get_text("https://baseballsavant.mlb.com/api")

    assert result == "ok"
    assert mock_session.get.await_count == 2


@pytest.mark.asyncio
async def test_retry_exhaustion_raises_last_status() -> None:
    client = HttpClient(max_retries=1, retry_backoff_base_seconds=0)
    first_response = MagicMock(status_code=503)
    second_response = MagicMock(status_code=504)

    mock_session = MagicMock()
    mock_session.get = AsyncMock(
        side_effect=[
            CurlHTTPError("Service Unavailable", response=first_response),
            CurlHTTPError("Gateway Timeout", response=second_response),
        ]
    )

    with patch.object(client, "_cffi_session", mock_session):
        with pytest.raises(PolarsBaseballHttpError) as exc_info:
            await client.get_text("https://baseballsavant.mlb.com/api")

    assert exc_info.value.status_code == 504
    assert mock_session.get.await_count == 2


@pytest.mark.asyncio
async def test_cffi_retries_transient_status_before_success() -> None:
    client = HttpClient(max_retries=1, retry_backoff_base_seconds=0)
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


@pytest.mark.asyncio
async def test_http_client_custom_impersonate_and_headers() -> None:
    client = HttpClient(impersonate=None, default_headers={"Custom-UA": "MyAgent"})

    with patch("polars_baseball._client.AsyncSession") as mock_session_class:
        client.get_cffi_session()
    mock_session_class.assert_called_once()
    assert "impersonate" not in mock_session_class.call_args.kwargs
    assert mock_session_class.call_args.kwargs["timeout"] == client._timeout


@pytest.mark.asyncio
async def test_http_client_default_behavior_impersonation() -> None:
    client = HttpClient()

    with patch("polars_baseball._client.AsyncSession") as mock_session_class:
        client.get_cffi_session()
    mock_session_class.assert_called_once()
    assert mock_session_class.call_args.kwargs["impersonate"] == "chrome"


@pytest.mark.asyncio
async def test_cffi_request_merges_default_headers() -> None:
    client = HttpClient(default_headers={"Header-A": "ValA"})
    mock_resp = MagicMock()
    mock_resp.text = "ok"
    mock_resp.raise_for_status.return_value = None
    mock_session = MagicMock()
    mock_session.get = AsyncMock(return_value=mock_resp)

    with patch.object(client, "_cffi_session", mock_session):
        await client.get_text("https://www.fangraphs.com/leaders", headers={"Header-B": "ValB"})

    mock_session.get.assert_called_once()
    _, kwargs = mock_session.get.call_args
    assert kwargs["headers"]["Header-A"] == "ValA"
    assert kwargs["headers"]["Header-B"] == "ValB"


@pytest.mark.asyncio
async def test_http_client_ssl_error_no_retry() -> None:
    import ssl

    client = HttpClient()
    ssl_exc = ssl.SSLCertVerificationError("SSL cert expired")
    transport_exc = PolarsBaseballTransportError(f"Network request failed: {ssl_exc}")
    transport_exc.__cause__ = ssl_exc

    call_count = 0

    async def counting_op() -> None:
        nonlocal call_count
        call_count += 1
        raise transport_exc

    with pytest.raises(PolarsBaseballTransportError):
        await client._with_retries(counting_op)

    assert call_count == 1


@pytest.mark.asyncio
async def test_rate_limit_uses_monotonic_clock() -> None:
    client = HttpClient(bref_requests_per_minute=60)
    assert client._bref_delay == 1.0

    with (
        patch("polars_baseball._client.time.monotonic", side_effect=[100.2, 101.0]) as mock_monotonic,
        patch("polars_baseball._client.asyncio.sleep", new_callable=AsyncMock) as mock_sleep,
    ):
        client._bref_last_request = 100.0
        await client._rate_limit()

        assert mock_monotonic.call_count == 2
        mock_sleep.assert_awaited_once_with(pytest.approx(0.8))
        assert client._bref_last_request == 101.0
