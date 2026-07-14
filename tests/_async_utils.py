"""Shared async test utilities for polars_baseball live/integration tests."""

import asyncio
import typing

import polars_baseball.context as pb_context
from polars_baseball.context import cleanup

T = typing.TypeVar("T")


def run_async(coro: typing.Awaitable[T]) -> T:
    """Run a coroutine in a new isolated event loop with clean context teardown.

    Creates a fresh event loop per call so live tests do not share async state.
    Cleans up the default HTTP context before closing to prevent resource leaks.
    """
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.run_until_complete(cleanup())
        pb_context._default_ctx = None
        loop.close()
