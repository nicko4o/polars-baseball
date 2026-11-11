> [!NOTE]
> All public data-fetching APIs are asynchronous. Use `await` inside an async environment, or wrap calls with `asyncio.run()` in scripts.

# FanGraphs Data Acquisition

Documentation and API reference for retrieving player and team leaderboards from FanGraphs.

---

## Namespace Helpers

For common queries, use helper functions under the `fangraphs` namespace (e.g. `client.fangraphs.batting(...)`).

### Functions

| Function | Description |
| --- | --- |
| `fangraphs.batting(start_season, ...)` | Player batting leaderboard. |
| `fangraphs.pitching(start_season, ...)` | Player pitching leaderboard. |
| `fangraphs.fielding(start_season, ...)` | Player fielding leaderboard. |
| `fangraphs.team_batting(start_season, ...)` | Team batting leaderboard. |
| `fangraphs.team_pitching(start_season, ...)` | Team pitching leaderboard. |
| `fangraphs.team_fielding(start_season, ...)` | Team fielding leaderboard. |
| `fangraphs.team_starters(start_season, ...)` | Team starting pitcher leaderboard (`stats=sta`). |
| `fangraphs.team_relievers(start_season, ...)` | Team relief pitcher leaderboard (`stats=rel`). |
| `fangraphs.season_schedule(team, season, ...)` | Team game-by-game season schedule and results. |
| `fangraphs.fg_data(start_season, ...)` | Direct custom leaderboard query endpoint. |

### Arguments

The namespace helpers accept the following keyword arguments:

| Field | Type | Default | Description |
| --- | --- | --- | --- |
| `start_season` | `int` | required | First season to retrieve. |
| `end_season` | `int \| None` | `start_season` | Final season to retrieve. |
| `stats_category` | `FangraphsStatsCategory` | `BATTING` | Category of data to fetch . |
| `league` | `FangraphsLeague \| str` | `ALL` | League filter (e.g. `"AL"`, `"NL"`). |
| `month` | `FangraphsMonth \| str` | `ALL` | Month or split filter. |
| `position` | `FangraphsPositions \| str` | `ALL` | Position filter. |
| `stat_columns` | `str \| list[str]` | `ALL` | Columns to return, or `ALL` for default. |
| `qual` | `int \| None` | `None` | Minimum plate appearances or innings pitched qualifier. |
| `split_seasons` | `bool` | `True` | `True` = season-level rows; `False` = aggregated over the range. |
| `on_active_roster` | `bool` | `False` | Only return active-roster players when `True`. |
| `minimum_age` / `maximum_age` | `int` | `0` / `100` | Player age filters. |
| `team` | `str` | `""` | Team abbreviation or ID. Use `"0,ts"` for team rows. |
| `filters` | `list[FanGraphsFilter] \| None` | `None` | Stat-level filters (e.g. `[FanGraphsFilter("HR", "gt", 40)]`). |
| `players` | `str` | `""` | Filter by specific player ID list string. |
| `max_results` | `int` | `1_000_000` | Maximum rows to retrieve. |

---

## Leaderboard Filtering (`filters`)

FanGraphs leaderboards support custom stat-level conditions (e.g. `HR > 40`, `AVG >= 0.300`). Pass a list of tuples or `FanGraphsFilter` objects via the `filters` argument in `client.fangraphs.*` helpers.

### Supported Syntax Options

- **Tuple Shorthand (Zero-import, Recommended)**: `[("HR", ">", 40), ("AVG", ">=", 0.300)]`
- **Mathematical Operators**: `[pb.fangraphs.FanGraphsFilter("HR", ">", 40)]`
- **Factory Methods**: `[pb.fangraphs.FanGraphsFilter.gt("HR", 40)]`
- **Enum Values**: `[pb.fangraphs.FanGraphsFilter("HR", pb.fangraphs.FanGraphsFilterOp.GT, 40)]`

```python
import polars_baseball as pb

# 1. Tuple Shorthand (Recommended)
filters_tuple = [("HR", ">", 40), ("AVG", ">=", 0.300)]

# 2. Mathematical Operators
filters_math = [pb.fangraphs.FanGraphsFilter("HR", ">", 40)]

# 3. Factory Methods
filters_factory = [pb.fangraphs.FanGraphsFilter.gt("HR", 40), pb.fangraphs.FanGraphsFilter.gte("AVG", 0.300)]

# 4. Typed Enum
filters_enum = [pb.fangraphs.FanGraphsFilter("HR", pb.fangraphs.FanGraphsFilterOp.GT, 40)]
```

### Operator Mappings

| Math Symbol / Code | Internal Value | Meaning |
| --- | --- | --- |
| `">"`, `"gt"` | `gt` | Greater than (`>`) |
| `">="`, `"gte"` | `gte` | Greater than or equal to (`>=`) |
| `"<"`, `"lt"` | `lt` | Less than (`<`) |
| `"<="`, `"lte"` | `lte` | Less than or equal to (`<=`) |
| `"=="`, `"="`, `"eq"` | `eq` | Equals (`=`) |
| `"!="`, `"ne"` | `ne` | Not equals (`!=`) |

---

## Output DataFrame Schema

FanGraphs functions (`batting`, `pitching`, `fielding`, `season_schedule`) return a `pl.DataFrame` with dynamic or requested stat columns.

### Standard Batting Leaderboard Fields

| Column Name | Polars Type | Description |
| --- | --- | --- |
| `IDfg` | `pl.Int64` | Unique FanGraphs player identifier. |
| `Season` | `pl.Int64` | Season year (e.g. `2026`). |
| `Name` | `pl.String` | Player name. |
| `Team` | `pl.String` | Team abbreviation (e.g. `"LAD"`, `"NYY"`). |
| `Age` | `pl.Int64` | Player age during season. |
| `G` | `pl.Int64` | Games played. |
| `AB` | `pl.Int64` | At bats. |
| `PA` | `pl.Int64` | Plate appearances. |
| `H` | `pl.Int64` | Hits. |
| `HR` | `pl.Int64` | Home runs. |
| `R` | `pl.Int64` | Runs scored. |
| `RBI` | `pl.Int64` | Runs batted in. |
| `SB` | `pl.Int64` | Stolen bases. |
| `BB%` | `pl.Float64` | Walk percentage. |
| `K%` | `pl.Float64` | Strikeout percentage. |
| `ISO` | `pl.Float64` | Isolated power. |
| `BABIP` | `pl.Float64` | Batting average on balls in play. |
| `AVG` | `pl.Float64` | Batting average. |
| `OBP` | `pl.Float64` | On-base percentage. |
| `SLG` | `pl.Float64` | Slugging percentage. |
| `wOBA` | `pl.Float64` | Weighted on-base average. |
| `wRC+` | `pl.Float64` | Weighted runs created plus (100 = league average). |
| `WAR` | `pl.Float64` | Wins above replacement. |

---

## Example

The following example shows how to use both the quick namespace helpers and custom queries.

```python
import asyncio

from polars_baseball import BaseballClient

async def main() -> None:
    async with BaseballClient() as client:
        # 1. Using client namespace helpers
        batting = await client.fangraphs.batting(start_season=2019)
        pitching = await client.fangraphs.pitching(start_season=2019)
        team_batting = await client.fangraphs.team_batting(start_season=2019)
        team_pitching = await client.fangraphs.team_pitching(start_season=2019)
        team_fielding = await client.fangraphs.team_fielding(start_season=2019)
        team_starters = await client.fangraphs.team_starters(start_season=2024, team="NYY")
        team_relievers = await client.fangraphs.team_relievers(start_season=2024, team="LAD")
        team_batting_1b = await client.fangraphs.team_batting(start_season=2024, position="1B")
        print("Namespace Batting:", batting.head(2))

        # 2. Using client namespace helpers with tuple filters
        filtered_batting = await client.fangraphs.batting(
            start_season=2024,
            filters=[("HR", ">", 40), ("AVG", ">=", 0.300)],
        )
        print("Filtered Batting (HR > 40, AVG >= .300):", filtered_batting.head(2))

        # 3. Using season_schedule for team results
        schedule = await client.fangraphs.season_schedule("NYY", 2024)
        print("Season Schedule:", schedule.head(2))

        # 4. Using fg_data directly for custom queries
        custom_df = await client.fangraphs.fg_data(start_season=2024, qual=50)
        print("Direct Query:", custom_df.head(2))

if __name__ == "__main__":
    asyncio.run(main())
```
