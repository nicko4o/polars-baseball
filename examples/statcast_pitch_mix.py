from __future__ import annotations

import argparse
import asyncio

import polars as pl

import polars_baseball as pb

DEFAULT_START_DATE = "2026-06-01"
DEFAULT_END_DATE = "2026-06-01"
DEFAULT_PITCHER_ID = 506433
PERCENT_MULTIPLIER = 100


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize Statcast pitch mix with Polars.")
    parser.add_argument("--start-date", default=DEFAULT_START_DATE)
    parser.add_argument("--end-date", default=DEFAULT_END_DATE)
    parser.add_argument("--pitcher-id", type=int, default=DEFAULT_PITCHER_ID)
    return parser.parse_args()


def _build_pitch_mix(df: pl.DataFrame) -> pl.DataFrame:
    if df.is_empty():
        return pl.DataFrame()

    return (
        df.group_by("pitch_type")
        .agg(
            pl.len().alias("pitch_count"),
            pl.col("release_speed").mean().round(1).alias("avg_velocity"),
        )
        .with_columns(
            (pl.col("pitch_count") / pl.col("pitch_count").sum() * PERCENT_MULTIPLIER).round(1).alias("usage_pct")
        )
        .sort("pitch_count", descending=True)
    )


async def _main() -> None:
    args = _parse_args()
    df = await pb.statcast_pitcher(
        start_dt=args.start_date,
        end_dt=args.end_date,
        player_id=args.pitcher_id,
    )
    print(_build_pitch_mix(df))


if __name__ == "__main__":
    asyncio.run(_main())
