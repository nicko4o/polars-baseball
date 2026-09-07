"""Internal concurrency primitives for polars_baseball."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Sequence
from typing import TypeVar, cast

T = TypeVar("T")


async def bounded_gather(
    tasks: Sequence[Callable[[], Awaitable[T]]],
    concurrency_limit: int,
    on_progress: Callable[[], None] | None = None,
) -> list[T]:
    """Execute task factories concurrently up to concurrency_limit.

    Tasks are only instantiated upon execution (lazy evaluation).
    If concurrency_limit <= 1, tasks are executed sequentially without worker tasks.
    In-flight tasks are cancelled on the first unhandled exception (fail-fast).
    """
    if not tasks:
        return []

    if concurrency_limit <= 1:
        return await _run_sequential(tasks, on_progress)

    return await _run_worker_pool(tasks, concurrency_limit, on_progress)


async def _run_sequential(
    tasks: Sequence[Callable[[], Awaitable[T]]],
    on_progress: Callable[[], None] | None,
) -> list[T]:
    results: list[T] = []
    for task in tasks:
        result = await task()
        results.append(result)
        if on_progress:
            on_progress()
    return results


async def _run_worker_pool(
    tasks: Sequence[Callable[[], Awaitable[T]]],
    concurrency_limit: int,
    on_progress: Callable[[], None] | None,
) -> list[T]:
    results: list[T | None] = [None] * len(tasks)
    queue: asyncio.Queue[tuple[int, Callable[[], Awaitable[T]]]] = asyncio.Queue()
    for idx, task in enumerate(tasks):
        queue.put_nowait((idx, task))

    async def worker() -> None:
        while True:
            try:
                idx, task = queue.get_nowait()
            except asyncio.QueueEmpty:
                break
            try:
                results[idx] = await task()
            finally:
                queue.task_done()
            if on_progress:
                on_progress()

    num_workers = min(concurrency_limit, len(tasks))
    worker_tasks = [asyncio.create_task(worker()) for _ in range(num_workers)]
    try:
        await asyncio.gather(*worker_tasks)
    except BaseException:
        for t in worker_tasks:
            if not t.done():
                t.cancel()
        await asyncio.gather(*worker_tasks, return_exceptions=True)
        raise

    return cast(list[T], results)
