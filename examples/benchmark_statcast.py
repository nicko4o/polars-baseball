from __future__ import annotations

import argparse
import asyncio
import time
import tracemalloc
from dataclasses import dataclass

import polars_baseball as pb

DEFAULT_START_DATE = "2024-04-01"
DEFAULT_END_DATE = "2024-04-07"
BYTES_PER_MIB = 1024 * 1024


@dataclass(frozen=True)
class BenchmarkResult:
    rows: int
    columns: int
    elapsed_seconds: float
    peak_mib: float


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Benchmark a Statcast fetch with polars-baseball.")
    parser.add_argument("--start-date", default=DEFAULT_START_DATE)
    parser.add_argument("--end-date", default=DEFAULT_END_DATE)
    parser.add_argument("--team", default=None)
    parser.add_argument("--serial", action="store_true", help="Disable parallel Statcast sub-queries.")
    return parser.parse_args()


async def _run_benchmark(start_date: str, end_date: str, team: str | None, parallel: bool) -> BenchmarkResult:
    tracemalloc.start()
    start = time.perf_counter()
    df = await pb.statcast(
        start_dt=start_date,
        end_dt=end_date,
        team=team,
        verbose=False,
        parallel=parallel,
    )
    elapsed_seconds = time.perf_counter() - start
    _current_bytes, peak_bytes = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    return BenchmarkResult(
        rows=df.height,
        columns=df.width,
        elapsed_seconds=elapsed_seconds,
        peak_mib=peak_bytes / BYTES_PER_MIB,
    )


async def _main() -> None:
    args = _parse_args()
    result = await _run_benchmark(
        start_date=args.start_date,
        end_date=args.end_date,
        team=args.team,
        parallel=not args.serial,
    )
    print(f"rows={result.rows}")
    print(f"columns={result.columns}")
    print(f"elapsed_seconds={result.elapsed_seconds:.3f}")
    print(f"python_peak_mib={result.peak_mib:.2f}")


if __name__ == "__main__":
    asyncio.run(_main())
