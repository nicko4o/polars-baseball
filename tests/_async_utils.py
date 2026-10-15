"""Shared async test utilities for polars_baseball live/integration tests."""

import asyncio
import typing

T = typing.TypeVar("T")


def run_async(coro: typing.Awaitable[T]) -> T:
    """Run a coroutine in a new isolated event loop."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()
