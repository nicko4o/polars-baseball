> [!NOTE]
> All public data-fetching APIs are asynchronous. Use `await` inside an async environment, or wrap calls with `asyncio.run()` in scripts.

# Statcast Pitcher Leaderboards

These functions retrieve Baseball Savant player leaderboards and pitch-level data as `polars.DataFrame` objects.

## Functions

| Function | Data |
| --- | --- |
| `statcast_pitcher` | Pitch-level Statcast data for one pitcher and date range. |
| `statcast_pitcher_exitvelo_barrels` | Batted-ball quality allowed by pitchers. |
| `statcast_pitcher_expected_stats` | Expected stats allowed by pitchers. |
| `statcast_pitcher_pitch_arsenal` | High-level pitch arsenal metrics. |
| `statcast_pitcher_arsenal_stats` | Outcome metrics by pitch arsenal. |
| `statcast_pitcher_pitch_movement` | Pitch movement metrics by pitch type. |
| `statcast_pitcher_active_spin` | Active-spin metrics. |
| `statcast_pitcher_percentile_ranks` | Pitcher percentile ranks. |
| `statcast_pitcher_spin_dir_comp` | Spin-direction comparisons between pitch types. |
| `statcast_pitcher_run_value` | Run value leaderboard data. |
| `statcast_pitcher_bat_tracking` | Bat-tracking data against pitchers. |

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
    pitches = await pb.statcast_pitcher(start_date="2024-05-06", end_date="2024-05-06", player_id=506433)
    arsenal = await pb.savant.pitcher_pitch_arsenal(2024, minP=250)
    print(pitches.head())
    print(arsenal.head())

if __name__ == "__main__":
    asyncio.run(main())
```
