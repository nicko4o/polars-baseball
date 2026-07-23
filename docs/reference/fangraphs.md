> [!NOTE]
> All public data-fetching APIs are asynchronous. Use `await` inside an async environment, or wrap calls with `asyncio.run()` in scripts.

# FanGraphs Data Acquisition

Documentation and API reference for retrieving player and team leaderboards from FanGraphs.

---

## Namespace Helpers

For common queries, use helper functions under the `fangraphs` namespace (e.g. `pb.fangraphs.batting(...)`).

### Functions

| Function | Description |
| --- | --- |
| `fangraphs.batting(start_season, ...)` | Player batting leaderboard. |
| `fangraphs.pitching(start_season, ...)` | Player pitching leaderboard. |
| `fangraphs.fielding(start_season, ...)` | Player fielding leaderboard. |
| `fangraphs.team_batting(start_season, ...)` | Team batting leaderboard. |
| `fangraphs.team_pitching(start_season, ...)` | Team pitching leaderboard. |
| `fangraphs.team_fielding(start_season, ...)` | Team fielding leaderboard. |

### Arguments

The namespace helpers accept all arguments supported by `FanGraphsRequest` directly as keyword arguments.

---

## Advanced Queries (`fg_data`)

Advanced callers can construct a `FanGraphsRequest` object and pass it directly to `fg_data` to execute custom or fine-tuned requests.

### Functions

- `fg_data(request: FanGraphsRequest) -> pl.DataFrame`

### `FanGraphsRequest` Attributes

Construct requests using classmethods: `FanGraphsRequest.batting(...)`, `FanGraphsRequest.pitching(...)`, `FanGraphsRequest.team_batting(...)`, etc.

| Field | Type | Default | Description |
| --- | --- | --- | --- |
| `start_season` | `int` | required | First season to retrieve. |
| `end_season` | `int | None` | `start_season` | Final season to retrieve. |
| `stats_category` | `FangraphsStatsCategory` | `BATTING` | Category of data to fetch. |
| `league` | `FangraphsLeague \| str` | `ALL` | League filter (e.g. `"AL"`, `"NL"`). |
| `month` | `FangraphsMonth \| str` | `ALL` | Month or split filter. |
| `position` | `FangraphsPositions \| str` | `ALL` | Position filter. |
| `stat_columns` | `str \| list[str]` | `ALL` | Columns to return, or `ALL` for default. |
| `qual` | `int \| None` | `None` | Minimum plate appearances or innings pitched qualifier. |
| `split_seasons` | `bool` | `True` | `True` = season-level rows; `False` = aggregated over the range. |
| `on_active_roster` | `bool` | `False` | Only return active-roster players when `True`. |
| `minimum_age` / `maximum_age` | `int` | `0` / `100` | Player age filters. |
| `team` | `str` | `""` | Team abbreviation or ID. Use `"0,ts"` for team rows. |
| `max_results` | `int` | `1_000_000` | Maximum rows to retrieve. |

---

## Example

The following example shows how to use both the quick namespace helpers and custom `FanGraphsRequest` queries.

```python
import asyncio

import polars_baseball as pb

async def main() -> None:
    # 1. Using quick namespace helpers
    batting = await pb.fangraphs.batting(start_season=2019)
    pitching = await pb.fangraphs.pitching(start_season=2019)
    team_batting = await pb.fangraphs.team_batting(start_season=2019)
    team_fielding = await pb.fangraphs.team_fielding(start_season=2019)
    team_pitching = await pb.fangraphs.team_pitching(start_season=2019)
    print("Namespace Batting:", batting.head(2))

    # 2. Using advanced fg_data with FanGraphsRequest
    req_batting = pb.FanGraphsRequest.batting(start_season=2026)
    req_qualified = pb.FanGraphsRequest.batting(start_season=2023, qual=50)
    req_split = pb.FanGraphsRequest.batting(start_season=2022, end_season=2026, split_seasons=True)
    
    season_df = await pb.fg_data(req_batting)
    qualified_df = await pb.fg_data(req_qualified)
    split_df = await pb.fg_data(req_split)
    print("Advanced Query:", season_df.head(2))

if __name__ == "__main__":
    asyncio.run(main())
```
