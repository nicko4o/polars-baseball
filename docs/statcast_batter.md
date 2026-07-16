> [!NOTE]
> All public data-fetching APIs are asynchronous. Use `await` inside an async environment, or wrap calls with `asyncio.run()` in scripts.

# Statcast Batter Leaderboards

These functions retrieve Baseball Savant player leaderboards and pitch-level data as `polars.DataFrame` objects.

## Functions

| Function | Data |
| --- | --- |
| `statcast_batter` | Pitch-level Statcast data for one batter and date range. |
| `statcast_batter_exitvelo_barrels` | Batted-ball exit velocity and barrel metrics. |
| `statcast_batter_expected_stats` | Expected statistics based on batted-ball quality. |
| `statcast_batter_percentile_ranks` | Percentile ranks for qualified batters. |
| `statcast_batter_pitch_arsenal` | Pitch arsenal faced by batters. |
| `statcast_batter_run_value` | Run value leaderboard data. |
| `statcast_batter_bat_tracking` | Bat-tracking leaderboard data. |

## Common Arguments

- `year`: Leaderboard season.
- `start_date` / `end_date`: Date range for pitch-level functions.
- `player_id`: MLBAM player ID for pitch-level player queries.
- `minPA`, `minP`, `minBBE`, `minSwings`: Minimum playing-time or event thresholds. Some functions accept `'q'` for qualified players.

## Data Availability

Pitch-level Statcast starts in 2008. Batted-ball quality metrics such as exit velocity and launch angle are available from 2015 onward.

## Example

```python
import asyncio

import polars_baseball as pb

async def main() -> None:
    pitches = await pb.statcast_batter(start_date="2024-05-06", end_date="2024-05-06", player_id=660271)
    expected = await pb.savant.batter_expected_stats(2024, minPA=100)
    print(pitches.head())
    print(expected.head())

if __name__ == "__main__":
    asyncio.run(main())
```
