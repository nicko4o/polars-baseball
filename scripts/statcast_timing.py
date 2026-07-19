import argparse
import asyncio
import sys
import time
import warnings
from typing import Final

from polars_baseball import statcast

warnings.warn(
    "scripts/statcast_timing.py is deprecated. Use `python -m benchmarks run <profile> --baseline` instead.",
    DeprecationWarning,
    stacklevel=2,
)

DEFAULT_TIME_THRESHOLD: Final[float] = 30.0
DEFAULT_START_DATE: Final[str] = "2018-08-01"
DEFAULT_END_DATE: Final[str] = "2018-08-10"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start-date", required=False, default=DEFAULT_START_DATE)
    parser.add_argument("--end-date", required=False, default=DEFAULT_END_DATE)
    parser.add_argument("--time-threshold", "-t", required=False, type=float, default=DEFAULT_TIME_THRESHOLD)
    return parser.parse_args()


async def main() -> None:
    args = _parse_args()
    start_time = time.time()
    _ = await statcast(args.start_date, args.end_date, verbose=False)
    end_time = time.time()
    query_time = end_time - start_time
    threshold_exceeded = query_time > args.time_threshold
    print(f"query took {query_time: .1f} seconds (expected less than {args.time_threshold: .1f})")
    sys.exit(int(threshold_exceeded))


if __name__ == "__main__":
    asyncio.run(main())
