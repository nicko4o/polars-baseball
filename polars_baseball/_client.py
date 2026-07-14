import asyncio
import time
from collections.abc import Awaitable, Callable, Mapping
from typing import TypeVar, cast

import httpx
from curl_cffi.requests import AsyncSession
from curl_cffi.requests.exceptions import RequestException as CurlRequestException

from polars_baseball._config import BREF_ROOT, DEFAULT_TIMEOUT, FG_ROOT
from polars_baseball.exceptions import PolarsBaseballHttpError

_BROWSER_HEADERS: Mapping[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
}

_CFFI_ROOTS: frozenset[str] = frozenset({BREF_ROOT, FG_ROOT})


SECONDS_PER_MINUTE = 60.0
DEFAULT_MAX_RETRIES = 2
DEFAULT_RETRY_BACKOFF_BASE_SECONDS = 0.25
BACKOFF_MULTIPLIER = 2.0
TRANSIENT_HTTP_STATUS_CODES = frozenset({429, 500, 502, 503, 504})

_T = TypeVar("_T")


class HttpClient:
    def __init__(
        self,
        bref_requests_per_minute: int = 10,
        extra_headers: Mapping[str, str] | None = None,
        max_retries: int = DEFAULT_MAX_RETRIES,
        retry_backoff_base_seconds: float = DEFAULT_RETRY_BACKOFF_BASE_SECONDS,
    ) -> None:
        if bref_requests_per_minute <= 0:
            raise ValueError(f"bref_requests_per_minute must be greater than 0, got {bref_requests_per_minute}")
        if max_retries < 0:
            raise ValueError(f"max_retries must be greater than or equal to 0, got {max_retries}")
        if retry_backoff_base_seconds < 0:
            raise ValueError(
                f"retry_backoff_base_seconds must be greater than or equal to 0, got {retry_backoff_base_seconds}"
            )
        self._httpx_client: httpx.AsyncClient | None = None
        self._cffi_session: AsyncSession | None = None
        self._lock = asyncio.Lock()
        self._bref_last_request = 0.0
        self._bref_delay = SECONDS_PER_MINUTE / bref_requests_per_minute
        self._extra_headers: dict[str, str] = dict(extra_headers) if extra_headers is not None else {}
        self._max_retries = max_retries
        self._retry_backoff_base_seconds = retry_backoff_base_seconds

    @property
    def extra_headers(self) -> dict[str, str]:
        return self._extra_headers

    @extra_headers.setter
    def extra_headers(self, value: Mapping[str, str] | None) -> None:
        self._extra_headers = dict(value) if value is not None else {}

    def get_httpx_client(self) -> httpx.AsyncClient:
        if self._httpx_client is None:
            self._httpx_client = httpx.AsyncClient(
                timeout=DEFAULT_TIMEOUT,
                follow_redirects=True,
                headers=_BROWSER_HEADERS,
            )
        return self._httpx_client

    def get_cffi_session(self) -> AsyncSession:
        if self._cffi_session is None:
            self._cffi_session = AsyncSession(
                impersonate="chrome",
                timeout=DEFAULT_TIMEOUT,
            )
        return self._cffi_session

    async def close(self) -> None:
        try:
            if self._httpx_client is not None:
                await self._httpx_client.aclose()
            if self._cffi_session is not None:
                await self._cffi_session.close()
        finally:
            self._httpx_client = None
            self._cffi_session = None

    @staticmethod
    def _needs_cffi(url: str) -> bool:
        return any(url.startswith(root) for root in _CFFI_ROOTS)

    @staticmethod
    def _str_params(params: Mapping[str, object] | None) -> dict[str, str] | None:
        if params is None:
            return None
        return {k: str(v) for k, v in params.items()}

    async def _rate_limit(self) -> None:
        async with self._lock:
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

    async def _with_retries(self, operation: Callable[[], Awaitable[_T]]) -> _T:
        for attempt in range(self._max_retries + 1):
            try:
                return await operation()
            except PolarsBaseballHttpError as exc:
                if attempt == self._max_retries or not self._is_transient_status(exc.status_code):
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
                raise PolarsBaseballHttpError(
                    f"HTTP status error: {e}",
                    status_code=e.response.status_code,
                ) from e
            except httpx.RequestError as e:
                raise PolarsBaseballHttpError(
                    f"Network request failed: {e}",
                    status_code=500,
                ) from e

        return await self._with_retries(request_once)

    async def _cffi_request(
        self,
        url: str,
        params: Mapping[str, object] | None = None,
        headers: Mapping[str, str] | None = None,
        rate_limited: bool = True,
    ) -> str:
        session = self.get_cffi_session()
        if rate_limited:
            await self._rate_limit()
        str_params = self._str_params(params)
        merged_headers = dict(self._extra_headers)
        if headers is not None:
            merged_headers.update(headers)

        async def request_once() -> str:
            str_headers = merged_headers if merged_headers else None
            try:
                response = await session.get(url, params=str_params, headers=str_headers)
                response.raise_for_status()  # type: ignore[no-untyped-call]
                return response.text
            except CurlRequestException as e:
                raise self._wrap_cffi_error(url, e) from e

        return await self._with_retries(request_once)

    @staticmethod
    def _wrap_cffi_error(url: str, error: CurlRequestException) -> PolarsBaseballHttpError:
        status_code = getattr(getattr(error, "response", None), "status_code", 500)
        label = "BRef" if url.startswith(BREF_ROOT) else "FanGraphs"
        return PolarsBaseballHttpError(
            f"{label} HTTP request failed: {error}",
            status_code=status_code,
        )

    async def get_text(
        self,
        url: str,
        *,
        params: Mapping[str, object] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> str:
        if self._needs_cffi(url):
            rate_limited = url.startswith(BREF_ROOT)
            return await self._cffi_request(url, params, headers=headers, rate_limited=rate_limited)
        return cast(str, await self._httpx_request(url, params, headers, as_text=True))

    async def get_bytes(
        self,
        url: str,
        *,
        params: Mapping[str, object] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> bytes:
        return cast(bytes, await self._httpx_request(url, params, headers, as_text=False))
