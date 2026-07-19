from __future__ import annotations

from unittest.mock import AsyncMock

import polars as pl
import pytest

from benchmarks.models import BenchmarkDimensions
from benchmarks.runner import run_benchmark


@pytest.mark.asyncio
async def test_runner_basic_metrics() -> None:
    async def fake_fn(**kwargs: object) -> pl.DataFrame:
        return pl.DataFrame({"a": [1, 2, 3], "b": [4.0, 5.0, 6.0]})

    dims = BenchmarkDimensions(api="test", start_date="2024-01-01", end_date="2024-01-02")
    run = await run_benchmark(fake_fn, dims, foo="bar")

    assert run.dimensions.api == "test"
    assert run.metrics.wall_time_seconds >= 0
    assert run.metrics.cpu_time_seconds >= 0
    assert run.metrics.peak_python_mib >= 0
    assert run.metrics.gc_collections >= 0
    assert run.metrics.result_rows == 3
    assert run.metrics.result_columns == 2
    assert run.version
    assert run.timestamp is not None


@pytest.mark.asyncio
async def test_runner_empty_dataframe() -> None:
    async def empty_fn(**kwargs: object) -> pl.DataFrame:
        return pl.DataFrame({"x": pl.Series([], dtype=pl.Int64)})

    dims = BenchmarkDimensions(api="test", start_date="2024-01-01", end_date="2024-01-02")
    run = await run_benchmark(empty_fn, dims)

    assert run.metrics.result_rows == 0
    assert run.metrics.result_columns == 1


@pytest.mark.asyncio
async def test_runner_metrics_are_consistent() -> None:
    async def slow_fn(**kwargs: object) -> pl.DataFrame:
        import asyncio

        await asyncio.sleep(0.05)
        return pl.DataFrame({"x": [1]})

    dims = BenchmarkDimensions(api="test", start_date="2024-01-01", end_date="2024-01-02")
    run = await run_benchmark(slow_fn, dims)

    assert run.metrics.wall_time_seconds >= 0.04
    assert run.metrics.cpu_time_seconds >= 0


@pytest.mark.asyncio
async def test_runner_with_mock() -> None:
    mock_fn = AsyncMock(return_value=pl.DataFrame({"col": [1, 2]}))
    dims = BenchmarkDimensions(api="mock_test", start_date="2024-01-01", end_date="2024-01-02")
    run = await run_benchmark(mock_fn, dims, extra_arg="value")

    mock_fn.assert_awaited_once_with(extra_arg="value")
    assert run.metrics.result_rows == 2
    assert run.metrics.result_columns == 1
