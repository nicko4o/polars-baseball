import asyncio
import ssl
import time
from collections.abc import Awaitable, Callable, Mapping
from typing import TypeVar, cast

import httpx
from curl_cffi.requests import AsyncSession
from curl_cffi.requests.exceptions import RequestException as CurlRequestException

from polars_baseball._config import DEFAULT_MAX_RETRIES, DEFAULT_TIMEOUT
from polars_baseball._http_policy import TransportKind, resolve_request_policy
from polars_baseball.exceptions import PolarsBaseballHttpError, PolarsBaseballTransportError

_BROWSER_HEADERS: Mapping[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
}

SECONDS_PER_MINUTE = 60.0
DEFAULT_RETRY_BACKOFF_BASE_SECONDS = 0.25
BACKOFF_MULTIPLIER = 2.0
TRANSIENT_HTTP_STATUS_CODES = frozenset({429, 500, 502, 503, 504})

_T = TypeVar("_T")


class HttpClient:
    """Async HTTP client with explicit timeout, retry, and provider rate-limit policy."""

    def __init__(
        self,
        bref_requests_per_minute: int | None = None,
        extra_headers: Mapping[str, str] | None = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_backoff_base_seconds: float = DEFAULT_RETRY_BACKOFF_BASE_SECONDS,
        timeout: float = DEFAULT_TIMEOUT,
        impersonate: str | None = "chrome",
        default_headers: Mapping[str, str] | None = None,
    ) -> None:
        if bref_requests_per_minute is not None and bref_requests_per_minute <= 0:
            raise ValueError(f"bref_requests_per_minute must be greater than 0, got {bref_requests_per_minute}")
        if max_retries < 0:
            raise ValueError(f"max_retries must be greater than or equal to 0, got {max_retries}")
        if retry_backoff_base_seconds < 0:
            raise ValueError(
                f"retry_backoff_base_seconds must be greater than or equal to 0, got {retry_backoff_base_seconds}"
            )
        if timeout <= 0:
            raise ValueError(f"timeout must be greater than 0, got {timeout}")
        self._httpx_client: httpx.AsyncClient | None = None
        self._cffi_session: AsyncSession | None = None
        self._lock = asyncio.Lock()
        self._bref_last_request = 0.0
        self._bref_delay = (
            SECONDS_PER_MINUTE / bref_requests_per_minute if bref_requests_per_minute is not None else None
        )
        self._extra_headers: dict[str, str] = dict(extra_headers) if extra_headers is not None else {}
        self._max_retries = max_retries
        self._retry_backoff_base_seconds = retry_backoff_base_seconds
        self._timeout = timeout
        self._impersonate = impersonate
        if default_headers is not None:
            self._default_headers: dict[str, str] = dict(default_headers)
        else:
            self._default_headers = dict(_BROWSER_HEADERS) if impersonate is not None else {}

    @property
    def extra_headers(self) -> dict[str, str]:
        return self._extra_headers

    @extra_headers.setter
    def extra_headers(self, value: Mapping[str, str] | None) -> None:
        self._extra_headers = dict(value) if value is not None else {}

    def get_httpx_client(self) -> httpx.AsyncClient:
        if self._httpx_client is None:
            self._httpx_client = httpx.AsyncClient(
                timeout=self._timeout,
                follow_redirects=True,
                headers=self._default_headers if self._default_headers else None,
            )
        return self._httpx_client

    def get_cffi_session(self) -> AsyncSession:
        if self._cffi_session is None:
            if self._impersonate is not None:
                self._cffi_session = AsyncSession(timeout=self._timeout, impersonate=self._impersonate)  # type: ignore[arg-type]  # curl_cffi stubs use Literal type
            else:
                self._cffi_session = AsyncSession(timeout=self._timeout)
        return self._cffi_session

    async def close(self) -> None:
        errors: list[Exception] = []
        if self._httpx_client is not None:
            try:
                await self._httpx_client.aclose()
            except Exception as e:
                errors.append(e)
            finally:
                self._httpx_client = None

        if self._cffi_session is not None:
            try:
                await self._cffi_session.close()
            except Exception as e:
                errors.append(e)
            finally:
                self._cffi_session = None

        if errors:
            if len(errors) == 1:
                raise errors[0]
            raise ExceptionGroup("Errors occurred during HttpClient close", errors)

    @staticmethod
    def _str_params(params: Mapping[str, object] | None) -> dict[str, str] | None:
        if params is None:
            return None
        return {k: str(v) for k, v in params.items()}

    async def _rate_limit(self) -> None:
        async with self._lock:
            if self._bref_delay is None:
                return
            now = time.time()
            elapsed = now - self._bref_last_request
            sleep_time = self._bref_delay - elapsed
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
            self._bref_last_request = time.time()

    @staticmethod
    def _is_transient_status(status_code: int) -> bool:
        return status_code in TRANSIENT_HTTP_STATUS_CODES

    def _retry_delay(self, attempt: int) -> float:
        return self._retry_backoff_base_seconds * (BACKOFF_MULTIPLIER**attempt)

    @staticmethod
    def _is_ssl_error(exc: BaseException) -> bool:
        curr: BaseException | None = exc
        while curr is not None:
            if isinstance(curr, ssl.SSLError | ssl.CertificateError):
                return True
            curr = curr.__cause__ or curr.__context__
        return False

    async def _with_retries(self, operation: Callable[[], Awaitable[_T]]) -> _T:
        for attempt in range(self._max_retries + 1):
            try:
                return await operation()
            except (PolarsBaseballHttpError, PolarsBaseballTransportError) as exc:
                status_code = getattr(exc, "status_code", 0)
                should_retry = (
                    isinstance(exc, PolarsBaseballTransportError) and not self._is_ssl_error(exc)
                ) or self._is_transient_status(status_code)
                if attempt == self._max_retries or not should_retry:
                    raise
                await asyncio.sleep(self._retry_delay(attempt))

        raise RuntimeError("retry loop exited without returning or raising")

    async def _httpx_request(
        self,
        url: str,
        params: Mapping[str, object] | None = None,
        headers: Mapping[str, str] | None = None,
        as_text: bool = True,
    ) -> str | bytes:
        client = self.get_httpx_client()
        str_params = self._str_params(params)
        merged_headers = dict(self._extra_headers)
        if headers is not None:
            merged_headers.update(headers)

        async def request_once() -> str | bytes:
            try:
                if merged_headers:
                    response = await client.get(url, params=str_params, headers=merged_headers)
                else:
                    response = await client.get(url, params=str_params)
                response.raise_for_status()
                return response.text if as_text else response.content
            except httpx.HTTPStatusError as e:
                msg = f"HTTP status error: {e}"
                if e.response.status_code == 403:
                    msg += " (Access forbidden; if this provider is Cloudflare protected, pass 'CF_CLEARANCE' or 'CF_COOKIE' via BaseballContext extra_headers)"
                raise PolarsBaseballHttpError(
                    msg,
                    status_code=e.response.status_code,
                ) from e
            except httpx.RequestError as e:
                raise PolarsBaseballTransportError(f"Network request failed: {e}") from e

        return await self._with_retries(request_once)

    async def _cffi_request(
        self,
        url: str,
        params: Mapping[str, object] | None = None,
        headers: Mapping[str, str] | None = None,
        rate_limited: bool = True,
    ) -> str:
        session = self.get_cffi_session()
        if rate_limited and self._bref_delay is not None:
            await self._rate_limit()
        str_params = self._str_params(params)
        merged_headers = {}
        if self._impersonate is None:
            merged_headers.update(self._default_headers)
        else:
            # Exclude default User-Agent to avoid interfering with curl-cffi impersonation
            for k, v in self._default_headers.items():
                if k.lower() != "user-agent":
                    merged_headers[k] = v
        merged_headers.update(self._extra_headers)
        if headers is not None:
            merged_headers.update(headers)

        async def request_once() -> str:
            str_headers = merged_headers if merged_headers else None
            try:
                response = await session.get(url, params=str_params, headers=str_headers)
                response.raise_for_status()  # type: ignore[no-untyped-call]  # curl_cffi stubs missing return type
                return response.text
            except CurlRequestException as e:
                raise self._wrap_cffi_error(url, e) from e

        return await self._with_retries(request_once)

    @staticmethod
    def _wrap_cffi_error(
        url: str, error: CurlRequestException
    ) -> PolarsBaseballHttpError | PolarsBaseballTransportError:
        response = getattr(error, "response", None)
        label = resolve_request_policy(url).provider_label
        if response is None:
            return PolarsBaseballTransportError(f"{label} network request failed: {error}")
        msg = f"{label} HTTP request failed: {error}"
        if response.status_code == 403 and label in ("BRef", "FanGraphs"):
            msg += " (Request blocked by Cloudflare Turnstile; pass 'CF_CLEARANCE' or 'CF_COOKIE' via BaseballContext extra_headers or use cached data)"
        return PolarsBaseballHttpError(
            msg,
            status_code=response.status_code,
        )

    async def get_text(
        self,
        url: str,
        *,
        params: Mapping[str, object] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> str:
        policy = resolve_request_policy(url)
        if policy.transport is TransportKind.BROWSER:
            return await self._cffi_request(url, params, headers=headers, rate_limited=policy.rate_limited)
        return cast(str, await self._httpx_request(url, params, headers, as_text=True))

    async def get_bytes(
        self,
        url: str,
        *,
        params: Mapping[str, object] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> bytes:
        return cast(bytes, await self._httpx_request(url, params, headers, as_text=False))
