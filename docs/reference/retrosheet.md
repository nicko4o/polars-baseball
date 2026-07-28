> [!NOTE]
> All public data-fetching APIs are asynchronous. Use `await` inside an async environment, or wrap calls with `asyncio.run()` in scripts.

# Retrosheet Data Acquisition

Retrosheet functions retrieve game logs, schedules, rosters, park codes, and event files.

## Functions

| Function | Data |
| --- | --- |
| `events(season, type="regular")` | Retrieves Retrosheet event files as a DataFrame with `season`, `event_type`, `filename`, and raw `content` columns. |
| `rosters(season)` | Season roster data. |
| `schedules(season)` | Season schedules. |
| `season_game_logs(season)` | Regular-season game logs. |
| `all_star_game_logs()` | All-Star game logs. |
| `wild_card_logs()` | Wild Card game logs. |
| `division_series_logs()` | Division Series game logs. |
| `lcs_logs()` | League Championship Series game logs. |
| `world_series_logs()` | World Series game logs. |
| `park_codes()` | Retrosheet park codes. |

---

## Output DataFrame Schema & Internal Definitions

Retrosheet schemas and column definitions are defined in [polars_baseball/_schemas/retrosheet.py](../../polars_baseball/_schemas/retrosheet.py).

### Endpoint Schema Summary

| Function | Primary Output Columns | Key Polars Types |
| --- | --- | --- |
| `rosters` | `player_id`, `last_name`, `first_name`, `bats`, `throws`, `team`, `pos` | `player_id`: `String`, `last_name`: `String`, `pos`: `String` |
| `schedules` | `date`, `game_number`, `day_of_week`, `visiting_team`, `home_team` | `date`: `String`, `game_number`: `Int64`, `visiting_team`: `String` |
| `game_logs` | `date`, `game_number`, `visiting_team`, `home_team`, `visiting_score`, `home_score` | `date`: `String`, `visiting_score`: `Int64`, `home_score`: `Int64` |
| `park_codes` | `park_id`, `name`, `aka`, `city`, `state`, `start_date`, `end_date`, `league` | `park_id`: `String`, `name`: `String`, `state`: `String` |

---

```python
import asyncio
import polars_baseball as pb

async def main() -> None:
    roster_df = await pb.retrosheet.rosters(2019)
    schedule_df = await pb.retrosheet.schedules(2019)
    parks_df = await pb.retrosheet.park_codes()
    print(roster_df.head())
    print(schedule_df.head())
    print(parks_df.head())

if __name__ == "__main__":
    asyncio.run(main())
```
