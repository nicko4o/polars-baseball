> [!NOTE]
> All public data-fetching APIs are asynchronous. Use `await` inside an async environment, or wrap calls with `asyncio.run()` in scripts.

# FanGraphs Data Acquisition

Use this when: you need FanGraphs player or team leaderboards.
Do not use this when: you need pitch-level Statcast rows or official MLB game endpoints.
Output grain: one row per player, team, or split returned by FanGraphs.
Source: FanGraphs.

FanGraphs data should be retrieved through the `fangraphs` namespace, such as `pb.fangraphs.batting(...)`. Advanced callers can still build a `FanGraphsRequest` and pass it to `fg_data(request)`.

## Namespace Helpers

| Function | Description |
| --- | --- |
| `fangraphs.batting(start_season, ...)` | Player batting leaderboard. |
| `fangraphs.pitching(start_season, ...)` | Player pitching leaderboard. |
| `fangraphs.fielding(start_season, ...)` | Player fielding leaderboard. |
| `fangraphs.team_batting(start_season, ...)` | Team batting leaderboard. |
| `fangraphs.team_pitching(start_season, ...)` | Team pitching leaderboard. |
| `fangraphs.team_fielding(start_season, ...)` | Team fielding leaderboard. |

## `FanGraphsRequest`

| Field | Type | Default | Description |
| --- | --- | --- | --- |
| `start_season` | `int` | required | First season to retrieve. |
| `end_season` | `int | None` | `start_season` | Final season to retrieve. |
| `stats_category` | `FangraphsStatsCategory` | `BATTING` | Category of data to fetch. |
| `league` | `FangraphsLeague \| str` | `ALL` | League filter. Strings (e.g. `"AL"`) are auto-parsed. |
| `month` | `FangraphsMonth \| str` | `ALL` | Month or split filter. `ALL` disables the filter. |
| `position` | `FangraphsPositions \| str` | `ALL` | Position filter. |
| `stat_columns` | `str \| list[str]` | `ALL` | Columns to return, or `ALL` for the default set. |
| `qual` | `int \| None` | `None` | Minimum playing-time threshold. `None` = FG default. |
| `split_seasons` | `bool` | `True` | `True` = season-level rows; `False` = aggregated. |
| `on_active_roster` | `bool` | `False` | When `True`, only active-roster players are returned. |
| `minimum_age` / `maximum_age` | `int` | `0` / `100` | Player age bounds. |
| `team` | `str` | `""` | Team filter. Use `"0,ts"` for aggregate team rows. |
| `max_results` | `int` | `1_000_000` | Maximum number of rows to request. |

Use factory classmethods for advanced request construction: `FanGraphsRequest.batting(start_season=2019)`, `.pitching(start_season=2019)`, `.team_batting(start_season=2019)`, etc.

## Example

```python
import asyncio

import polars_baseball as bp


async def main() -> None:
    batting = await bp.fangraphs.batting(start_season=2019)
    pitching = await bp.fangraphs.pitching(start_season=2019)
    team_batting = await bp.fangraphs.team_batting(start_season=2019)
    team_fielding = await bp.fangraphs.team_fielding(start_season=2019)
    team_pitching = await bp.fangraphs.team_pitching(start_season=2019)
    print(batting.head())
    print(pitching.head())
    print(team_batting.head())
    print(team_fielding.head())
    print(team_pitching.head())


if __name__ == "__main__":
    asyncio.run(main())
```
