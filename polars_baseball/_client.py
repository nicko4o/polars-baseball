import asyncio
import logging
import os
import random
import ssl
import threading
import time
import weakref
from collections.abc import Awaitable, Callable, Mapping
from email.utils import parsedate_to_datetime
from typing import Final, TypeVar, cast

from curl_cffi.requests import AsyncSession
from curl_cffi.requests.exceptions import RequestException as CurlRequestException

from polars_baseball._concurrency import LoopBoundLockRegistry
from polars_baseball._config import DEFAULT_MAX_RETRIES, DEFAULT_TIMEOUT
from polars_baseball._http_policy import resolve_request_policy
from polars_baseball.exceptions import (
    PolarsBaseballHttpClientError,
    PolarsBaseballHttpError,
    PolarsBaseballHttpServerError,
    PolarsBaseballTransportError,
)

logger = logging.getLogger(__name__)

_BROWSER_HEADERS: Mapping[str, str] = {
    "User-Agent": (
        "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
    ),
}

SECONDS_PER_MINUTE = 60.0
DEFAULT_RETRY_BACKOFF_BASE_SECONDS = 0.25
BACKOFF_MULTIPLIER = 2.0
TRANSIENT_HTTP_STATUS_CODES = frozenset({429, 500, 502, 503, 504})
IDEMPOTENT_HTTP_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
MAX_RETRY_AFTER_SECONDS: Final[float] = 60.0
_BREF_RATE_LIMIT_LOCK_KEY: Final[str] = "bref_rate_limit"

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
        self._sessions: weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, AsyncSession] = weakref.WeakKeyDictionary()
        self._session_guard = threading.Lock()
        self._locks = LoopBoundLockRegistry()
        self._rate_limits: dict[str, float] = {}
        self._rate_limit_last_request: dict[str, float] = {}
        if bref_requests_per_minute is not None:
            self._rate_limits[_BREF_RATE_LIMIT_LOCK_KEY] = SECONDS_PER_MINUTE / bref_requests_per_minute
        self._extra_headers: dict[str, str] = self._resolve_extra_headers(extra_headers)
        self._max_retries = max_retries
        self._retry_backoff_base_seconds = retry_backoff_base_seconds
        self._timeout = timeout
        self._impersonate = impersonate
        if default_headers is not None:
            self._default_headers: dict[str, str] = dict(default_headers)
        else:
            self._default_headers = dict(_BROWSER_HEADERS) if impersonate is not None else {}

    @property
    def _bref_delay(self) -> float | None:
        return self._rate_limits.get(_BREF_RATE_LIMIT_LOCK_KEY)

    @_bref_delay.setter
    def _bref_delay(self, value: float | None) -> None:
        if value is None:
            self._rate_limits.pop(_BREF_RATE_LIMIT_LOCK_KEY, None)
        else:
            self._rate_limits[_BREF_RATE_LIMIT_LOCK_KEY] = value

    @property
    def _bref_last_request(self) -> float:
        return self._rate_limit_last_request.get(_BREF_RATE_LIMIT_LOCK_KEY, 0.0)

    @_bref_last_request.setter
    def _bref_last_request(self, value: float) -> None:
        self._rate_limit_last_request[_BREF_RATE_LIMIT_LOCK_KEY] = value

    @property
    def extra_headers(self) -> dict[str, str]:
        return self._extra_headers

    @extra_headers.setter
    def extra_headers(self, value: Mapping[str, str] | None) -> None:
        self._extra_headers = dict(value) if value is not None else {}

    @staticmethod
    def _resolve_extra_headers(extra_headers: Mapping[str, str] | None) -> dict[str, str]:
        resolved: dict[str, str] = {}
        cf_cookie = os.environ.get("CF_COOKIE")
        cf_clearance = os.environ.get("CF_CLEARANCE")
        user_agent = os.environ.get("USER_AGENT")

        if cf_cookie:
            resolved["Cookie"] = cf_cookie
        elif cf_clearance:
            resolved["Cookie"] = f"cf_clearance={cf_clearance}"
        if user_agent:
            resolved["User-Agent"] = user_agent

        if extra_headers is not None:
            resolved.update(extra_headers)
        return resolved

    def _create_session(self) -> AsyncSession:
        if self._impersonate is not None:
            return AsyncSession(timeout=self._timeout, impersonate=self._impersonate)  # type: ignore[arg-type]
        return AsyncSession(timeout=self._timeout)

    def get_cffi_session(self) -> AsyncSession:
        loop = asyncio.get_running_loop()
        with self._session_guard:
            session = self._sessions.get(loop)
            if session is None:
                session = self._create_session()
                self._sessions[loop] = session
            return session

    async def close(self) -> None:
        to_close: list[AsyncSession] = []
        with self._session_guard:
            to_close.extend(self._sessions.values())
            self._sessions.clear()

        for session in to_close:
            try:
                await session.close()
            except (CurlRequestException, RuntimeError, OSError) as exc:
                logger.debug("Failed to close HTTP session cleanly: %s", exc)

    @staticmethod
    def _str_params(params: Mapping[str, object] | None) -> dict[str, str] | None:
        if params is None:
            return None
        return {k: str(v) for k, v in params.items()}

    async def _rate_limit(self, lock_key: str = _BREF_RATE_LIMIT_LOCK_KEY) -> None:
        delay = self._rate_limits.get(lock_key)
        if delay is None:
            return
        async with self._locks.get_lock(lock_key):
            now = time.monotonic()
            last = self._rate_limit_last_request.get(lock_key, 0.0)
            elapsed = now - last
            sleep_time = delay - elapsed
            if sleep_time > 0:
                await asyncio.sleep(sleep_time)
            self._rate_limit_last_request[lock_key] = time.monotonic()

    @staticmethod
    def _is_transient_status(status_code: int) -> bool:
        return status_code in TRANSIENT_HTTP_STATUS_CODES

    def _retry_delay(self, attempt: int) -> float:
        base_delay = self._retry_backoff_base_seconds * (BACKOFF_MULTIPLIER**attempt)
        if base_delay <= 0:
            return 0.0
        return random.uniform(0.5 * base_delay, 1.5 * base_delay)

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
                retry_after = getattr(exc, "retry_after", None)
                if retry_after is not None and retry_after > 0:
                    delay = retry_after
                else:
                    delay = self._retry_delay(attempt)
                await asyncio.sleep(delay)

        raise RuntimeError("retry loop exited without returning or raising")

    @staticmethod
    def _parse_retry_after(headers: Mapping[str, str] | None) -> float | None:
        if not headers:
            return None
        raw_val: str | None = None
        for k, v in headers.items():
            if k.lower() == "retry-after":
                raw_val = v
                break
        if raw_val is None:
            return None
        raw_str = raw_val.strip()
        if not raw_str:
            return None
        try:
            seconds = float(raw_str)
            if seconds >= 0:
                return min(seconds, MAX_RETRY_AFTER_SECONDS)
        except ValueError:
            try:
                dt = parsedate_to_datetime(raw_str)
                seconds = dt.timestamp() - time.time()
                if seconds > 0:
                    return min(seconds, MAX_RETRY_AFTER_SECONDS)
            except Exception:
                pass
        return None

    async def _request(
        self,
        url: str,
        *,
        method: str = "GET",
        params: Mapping[str, object] | None = None,
        headers: Mapping[str, str] | None = None,
        json_data: Mapping[str, object] | None = None,
        as_text: bool = True,
        rate_limited: bool = False,
        retry_non_idempotent: bool = False,
    ) -> str | bytes:
        session = self.get_cffi_session()
        policy = resolve_request_policy(url)
        lock_key = policy.rate_limit_lock_key or _BREF_RATE_LIMIT_LOCK_KEY
        if (rate_limited or policy.rate_limited) and lock_key in self._rate_limits:
            await self._rate_limit(lock_key)
        str_params = self._str_params(params)
        merged_headers: dict[str, str] = {}
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

        async def request_once() -> str | bytes:
            str_headers = merged_headers if merged_headers else None
            try:
                if method.upper() == "POST":
                    json_payload = dict(json_data) if json_data is not None else None
                    response = await session.post(url, json=json_payload, headers=str_headers)
                else:
                    response = await session.get(url, params=str_params, headers=str_headers)
                response.raise_for_status()  # type: ignore[no-untyped-call]  # curl_cffi stubs missing return type
                return response.text if as_text else response.content
            except CurlRequestException as e:
                raise self._wrap_cffi_error(url, e) from e

        is_idempotent = method.upper() in IDEMPOTENT_HTTP_METHODS
        if is_idempotent or retry_non_idempotent:
            return await self._with_retries(request_once)
        return await request_once()

    @staticmethod
    def _create_http_error(msg: str, status_code: int, retry_after: float | None = None) -> PolarsBaseballHttpError:
        if 400 <= status_code < 500:
            return PolarsBaseballHttpClientError(msg, status_code=status_code, retry_after=retry_after)
        return PolarsBaseballHttpServerError(msg, status_code=status_code, retry_after=retry_after)

    @classmethod
    def _wrap_cffi_error(
        cls, url: str, error: CurlRequestException
    ) -> PolarsBaseballHttpError | PolarsBaseballTransportError:
        response = getattr(error, "response", None)
        policy = resolve_request_policy(url)
        label = policy.provider_label
        if response is None:
            return PolarsBaseballTransportError(f"{label} network request failed: {error}")
        msg = f"{label} HTTP request failed: {error}"
        if response.status_code == 403:
            if policy.is_cloudflare_protected:
                msg += " (Request blocked by Cloudflare Turnstile; pass 'CF_CLEARANCE' or 'CF_COOKIE' via BaseballClient extra_headers or use cached data)"
            else:
                msg += " (Access forbidden; if this provider is Cloudflare protected, pass 'CF_CLEARANCE' or 'CF_COOKIE' via BaseballClient extra_headers)"
        retry_after = cls._parse_retry_after(getattr(response, "headers", None))
        return cls._create_http_error(
            msg,
            status_code=response.status_code,
            retry_after=retry_after,
        )

    async def get_text(
        self,
        url: str,
        *,
        params: Mapping[str, object] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> str:
        policy = resolve_request_policy(url)
        return cast(
            str,
            await self._request(
                url,
                method="GET",
                params=params,
                headers=headers,
                as_text=True,
                rate_limited=policy.rate_limited,
            ),
        )

    async def get_bytes(
        self,
        url: str,
        *,
        params: Mapping[str, object] | None = None,
        headers: Mapping[str, str] | None = None,
    ) -> bytes:
        policy = resolve_request_policy(url)
        return cast(
            bytes,
            await self._request(
                url,
                method="GET",
                params=params,
                headers=headers,
                as_text=False,
                rate_limited=policy.rate_limited,
            ),
        )

    async def post_json(
        self,
        url: str,
        json_data: Mapping[str, object],
        *,
        headers: Mapping[str, str] | None = None,
        retry_non_idempotent: bool = False,
    ) -> str:
        policy = resolve_request_policy(url)
        return cast(
            str,
            await self._request(
                url,
                method="POST",
                headers=headers,
                json_data=json_data,
                as_text=True,
                rate_limited=policy.rate_limited,
                retry_non_idempotent=retry_non_idempotent,
            ),
        )
