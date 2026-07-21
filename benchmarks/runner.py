from __future__ import annotations

import gc
import time
import tracemalloc
from collections.abc import Awaitable, Callable
from datetime import UTC, datetime

import polars as pl

from polars_baseball import __version__

from .models import BenchmarkDimensions, BenchmarkMetrics, BenchmarkRun


def _extract_shape(result: pl.DataFrame | list[pl.DataFrame]) -> tuple[int, int]:
    if isinstance(result, list):
        if not result:
            return (0, 0)
        rows = sum(df.height for df in result)
        cols = result[0].width
        return (rows, cols)
    return (result.height, result.width)


async def run_benchmark(
    fn: Callable[..., Awaitable[pl.DataFrame | list[pl.DataFrame]]],
    dimensions: BenchmarkDimensions,
    /,
    **kwargs: object,
) -> BenchmarkRun:
    gc.collect()
    gc_before = sum(gc.get_count())
    tracemalloc.start()
    start_wall = time.perf_counter()
    start_cpu = time.process_time()

    result = await fn(**kwargs)

    end_cpu = time.process_time()
    end_wall = time.perf_counter()
    _current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    gc_after = sum(gc.get_count())

    rows, cols = _extract_shape(result)

    return BenchmarkRun(
        dimensions=dimensions,
        metrics=BenchmarkMetrics(
            wall_time_seconds=end_wall - start_wall,
            cpu_time_seconds=end_cpu - start_cpu,
            peak_python_mib=peak / (1024 * 1024),
            gc_collections=gc_after - gc_before,
            result_rows=rows,
            result_columns=cols,
        ),
        timestamp=datetime.now(UTC),
        version=__version__,
    )
