from __future__ import annotations

import argparse
import asyncio

import polars_baseball as pb

DEFAULT_SEASON = 2024
DEFAULT_QUALIFICATION = 100
DEFAULT_MAX_RESULTS = 20


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch a FanGraphs batting leaderboard.")
    parser.add_argument("--season", type=int, default=DEFAULT_SEASON)
    parser.add_argument("--qual", type=int, default=DEFAULT_QUALIFICATION)
    parser.add_argument("--max-results", type=int, default=DEFAULT_MAX_RESULTS)
    return parser.parse_args()


async def _main() -> None:
    args = _parse_args()
    request = pb.FanGraphsRequest.batting(
        start_season=args.season,
        end_season=args.season,
        qual=args.qual,
        max_results=args.max_results,
    )
    df = await pb.fg_data(request)
    print(df.head(args.max_results))


if __name__ == "__main__":
    asyncio.run(_main())
