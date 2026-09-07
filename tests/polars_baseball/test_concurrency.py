import asyncio
from typing import Any

import pytest

from polars_baseball._concurrency import bounded_gather


@pytest.mark.asyncio
async def test_bounded_gather_bounds_concurrent_executions() -> None:
    active = 0
    peak = 0
    lock = asyncio.Lock()

    async def make_task(i: int) -> int:
        nonlocal active, peak
        async with lock:
            active += 1
            if active > peak:
                peak = active
        await asyncio.sleep(0.01)
        async with lock:
            active -= 1
        return i * 2

    limit = 3
    tasks = [lambda i=i: make_task(i) for i in range(15)]
    results = await bounded_gather(tasks, concurrency_limit=limit)

    assert peak <= limit
    assert results == [i * 2 for i in range(15)]


@pytest.mark.asyncio
async def test_bounded_gather_sequential_when_limit_one() -> None:
    active = 0
    peak = 0

    async def make_task(i: int) -> int:
        nonlocal active, peak
        active += 1
        if active > peak:
            peak = active
        await asyncio.sleep(0.001)
        active -= 1
        return i

    tasks = [lambda i=i: make_task(i) for i in range(5)]
    results = await bounded_gather(tasks, concurrency_limit=1)

    assert peak == 1
    assert results == list(range(5))


@pytest.mark.asyncio
async def test_bounded_gather_lazy_execution() -> None:
    instantiated = 0

    def make_task(i: int) -> Any:
        async def _coro() -> int:
            nonlocal instantiated
            instantiated += 1
            await asyncio.sleep(0.005)
            return i

        return _coro()

    tasks = [lambda i=i: make_task(i) for i in range(10)]
    assert instantiated == 0

    results = await bounded_gather(tasks, concurrency_limit=2)
    assert results == list(range(10))
    assert instantiated == 10


@pytest.mark.asyncio
async def test_bounded_gather_fail_fast_cancels_remaining() -> None:
    cancelled_count = 0

    async def bad_task() -> int:
        await asyncio.sleep(0.005)
        raise RuntimeError("boom")

    async def slow_task() -> int:
        nonlocal cancelled_count
        try:
            await asyncio.sleep(1.0)
            return 42
        except asyncio.CancelledError:
            cancelled_count += 1
            raise

    tasks = [slow_task, bad_task, slow_task, slow_task]

    with pytest.raises(RuntimeError, match="boom"):
        await bounded_gather(tasks, concurrency_limit=2)

    assert cancelled_count >= 1


@pytest.mark.asyncio
async def test_bounded_gather_empty_tasks() -> None:
    results = await bounded_gather([], concurrency_limit=5)
    assert results == []


@pytest.mark.asyncio
async def test_bounded_gather_calls_on_progress() -> None:
    progress_count = 0

    def on_progress() -> None:
        nonlocal progress_count
        progress_count += 1

    async def task(i: int) -> int:
        await asyncio.sleep(0.001)
        return i

    tasks = [lambda i=i: task(i) for i in range(5)]
    await bounded_gather(tasks, concurrency_limit=2, on_progress=on_progress)

    assert progress_count == 5
