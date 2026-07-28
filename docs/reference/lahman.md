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

---

## Output DataFrame Schema

Lahman functions return a `pl.DataFrame` preserving original Lahman relational column names and data types.

### Key Table Schema Summary

| Function | Primary Columns | Key Polars Types |
| --- | --- | --- |
| `people()` | `playerID`, `birthYear`, `nameFirst`, `nameLast`, `weight`, `height`, `bats`, `throws`, `bbrefID` | `playerID`: `String`, `nameLast`: `String`, `birthYear`: `Int64` |
| `batting()` | `playerID`, `yearID`, `stint`, `teamID`, `lgID`, `G`, `AB`, `R`, `H`, `2B`, `3B`, `HR`, `RBI`, `SB`, `CS`, `BB`, `SO` | `playerID`: `String`, `yearID`: `Int64`, `HR`: `Int64` |
| `pitching()` | `playerID`, `yearID`, `stint`, `teamID`, `lgID`, `W`, `L`, `G`, `GS`, `CG`, `SHO`, `SV`, `IPouts`, `H`, `ER`, `HR`, `BB`, `SO`, `ERA` | `playerID`: `String`, `yearID`: `Int64`, `ERA`: `Float64` |
| `teams_core()` | `yearID`, `lgID`, `teamID`, `franchID`, `divID`, `Rank`, `G`, `W`, `L`, `DivWin`, `WCWin`, `LgWin`, `WSWin`, `R`, `RA`, `name` | `yearID`: `Int64`, `teamID`: `String`, `W`: `Int64` |

---

```python
import asyncio
import polars_baseball as pb

async def main() -> None:
    await pb.lahman.download_lahman()  # validates and caches the upstream archive fallback
    people_df = await pb.lahman.people()
    batting_df = await pb.lahman.batting()
    teams_df = await pb.lahman.teams_core()
    print(people_df.head())
    print(batting_df.head())
    print(teams_df.head())

if __name__ == "__main__":
    asyncio.run(main())
```
