> [!NOTE]
> All public data-fetching APIs are asynchronous. Use `await` inside an async environment, or wrap calls with `asyncio.run()` in scripts.

# Retrosheet Data Acquisition

Retrosheet functions retrieve game logs, schedules, rosters, park codes, and event files.

## Functions

| Function | Data |
| --- | --- |
| `events(season, type="regular")` | Retrieves Retrosheet event files as a dictionary mapping filenames to bytes. |
| `rosters(season)` | Season roster data. |
| `schedules(season)` | Season schedules. |
| `season_game_logs(season)` | Regular-season game logs. |
| `all_star_game_logs()` | All-Star game logs. |
| `wild_card_logs()` | Wild Card game logs. |
| `division_series_logs()` | Division Series game logs. |
| `lcs_logs()` | League Championship Series game logs. |
| `world_series_logs()` | World Series game logs. |
| `park_codes()` | Retrosheet park codes. |

## Example

```python
import asyncio
from polars_baseball.apis.retrosheet import park_codes, rosters, schedules

async def main() -> None:
    roster_df = await rosters(2019)
    schedule_df = await schedules(2019)
    parks_df = await park_codes()
    print(roster_df.head())
    print(schedule_df.head())
    print(parks_df.head())

if __name__ == "__main__":
    asyncio.run(main())
```
