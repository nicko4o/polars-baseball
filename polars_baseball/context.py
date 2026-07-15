import threading
from dataclasses import dataclass, field

from polars_baseball._cache import CacheAdapter, _set_default_cache_context_resolver, global_cache
from polars_baseball._client import HttpClient


@dataclass
class BaseballContext:
    """Context container for HTTP client and caching adapter.

    Supports the async context manager protocol to ensure that resources (e.g., HTTP sessions)
    are cleaned up automatically upon exit.

    Warning:
        If you pass a shared HttpClient instance to multiple BaseballContexts, exiting one context
        will close the shared HTTP client, affecting other contexts. In such cases, manage client
        lifecycles manually instead of using context managers.
    """

    http: HttpClient = field(default_factory=HttpClient)
    cache: CacheAdapter = field(default_factory=lambda: global_cache)

    async def __aenter__(self) -> "BaseballContext":
        return self

    async def __aexit__(
        self,
        _exc_type: type[BaseException] | None,
        _exc_val: BaseException | None,
        _exc_tb: object | None,
    ) -> None:
        await self.close()

    async def close(self) -> None:
        """Close HTTP resources owned by this context."""
        # Delegate to cleanup() so the singleton is reset if this instance is
        # the current default context.
        await cleanup(self)


_default_ctx: BaseballContext | None = None
# Protects lazy initialization of _default_ctx (double-checked locking pattern).
_default_ctx_lock = threading.Lock()


def default_context() -> BaseballContext:
    global _default_ctx
    # Fast path: already initialized, no lock acquisition needed.
    if _default_ctx is not None:
        return _default_ctx
    with _default_ctx_lock:
        # Re-check inside the lock to handle races between the fast-path check
        # and lock acquisition.
        if _default_ctx is None:
            _default_ctx = BaseballContext()
    return _default_ctx


_set_default_cache_context_resolver(default_context)


async def cleanup(ctx: BaseballContext | None = None) -> None:
    """Close HTTP resources and reset the default context singleton if applicable.

    When called without arguments, the current default singleton is targeted and
    the singleton reference is atomically cleared before closing the HTTP client,
    so no other caller can observe a half-closed client.

    Args:
        ctx: Context to clean up. If ``None``, the current default singleton is
             targeted. Passing an explicit context that is not the singleton
             cleans it up without touching the singleton.
    """
    global _default_ctx
    if ctx is not None:
        await ctx.http.close()
        # Reset singleton only if the caller passed the singleton itself.
        with _default_ctx_lock:
            if _default_ctx is ctx:
                _default_ctx = None
    else:
        # Atomically grab and clear the singleton before closing so concurrent
        # callers cannot observe a dead client via default_context().
        with _default_ctx_lock:
            target = _default_ctx
            _default_ctx = None
        if target is not None:
            await target.http.close()
