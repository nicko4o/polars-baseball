from __future__ import annotations

import argparse
import asyncio

import polars_baseball as pb

DEFAULT_DATE = "2024-05-06"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch MLB schedule data from the MLB Stats API.")
    parser.add_argument("--date", default=DEFAULT_DATE)
    parser.add_argument("--team-id", type=int, default=None)
    return parser.parse_args()


async def _main() -> None:
    args = _parse_args()
    df = await pb.mlb.schedule(date=args.date, team_id=args.team_id)
    print(df)


if __name__ == "__main__":
    asyncio.run(_main())
