> [!NOTE]
> All public data-fetching APIs are asynchronous. Use `await` inside an async environment, or wrap calls with `asyncio.run()` in scripts.

# Lahman Data Acquisition

Lahman functions retrieve compiled Parquet tables from cache or `POLARS_BASEBALL_DATASETS_URL`. If no compiled dataset root is configured, the data gateway compiles the requested table from the upstream ZIP archive and stores only that table as Parquet.

## Tables

| Function | Table |
| --- | --- |
| `people()` | Player biographical and ID data. |
| `parks()` | Ballpark IDs and metadata. |
| `all_star_full()` | All-Star rosters. |
| `appearances()` | Player appearances by team, season, and position. |
| `awards_managers()` | Manager awards. |
| `awards_players()` | Player awards. |
| `awards_share_managers()` | Manager award vote shares. |
| `awards_share_players()` | Player award vote shares. |
| `batting()` / `batting_post()` | Regular-season and postseason batting. |
| `pitching()` / `pitching_post()` | Regular-season and postseason pitching. |
| `fielding()` / `fielding_post()` | Regular-season and postseason fielding. |
| `fielding_of()` / `fielding_of_split()` | Outfield and outfield-split fielding data. |
| `college_playing()` | College playing records. |
| `hall_of_fame()` | Hall of Fame voting. |
| `home_games()` | Home-game attendance and park data. |
| `managers()` / `managers_half()` | Manager records. |
| `salaries()` | Salary data. |
| `schools()` | School lookup data. |
| `series_post()` | Postseason series results. |
| `teams_core()` / `teams_upstream()` / `teams_franchises()` / `teams_half()` | Team tables. |

## Example

```python
import asyncio
from polars_baseball.apis.lahman import batting, download_lahman, people, teams_core

async def main() -> None:
    await download_lahman()  # validates and caches the upstream archive fallback
    people_df = await people()
    batting_df = await batting()
    teams_df = await teams_core()
    print(people_df.head())
    print(batting_df.head())
    print(teams_df.head())

if __name__ == "__main__":
    asyncio.run(main())
```
