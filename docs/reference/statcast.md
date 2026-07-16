> [!NOTE]
> All public data-fetching APIs are asynchronous. Use `await` inside an async environment, or wrap calls with `asyncio.run()` in scripts.

# Statcast

Use this when: you need pitch-level Statcast rows for a date range.
Do not use this when: you only need official schedules, rosters, boxscores, or standings.
Output grain: one row per pitch.
Source: Baseball Savant.

`statcast(start_date: str | None = None, end_date: str | None = None, team: str | None = None, verbose: bool = True, parallel: bool = True) -> pl.DataFrame`

Retrieves pitch-level Statcast data from Baseball Savant for a date range.

## Returned Data

Returns one row per pitch as a `polars.DataFrame`. Baseball Savant documents CSV columns in [CSV documentation](https://baseballsavant.mlb.com/csv-docs).

## Arguments

- `start_date`: First date in `YYYY-MM-DD` format. If omitted, yesterday is used.
- `end_date`: Last date in `YYYY-MM-DD` format. If omitted, only `start_date` is queried.
- `team`: Optional team abbreviation such as `BOS`, `SEA`, or `NYY`.
- `verbose`: Print progress output.
- `parallel`: Run large date-range requests concurrently on the event loop.

`start_dt` and `end_dt` remain supported as backward-compatible aliases.

## Data Availability

Pitch-tracking Statcast data starts in 2008. Launch-speed and launch-angle metrics are available from 2015 onward.

## Single Game

`statcast_single_game(game_pk: str | int) -> pl.DataFrame`

Retrieves Statcast data for one MLB game.

- `game_pk`: MLB Advanced Media game identifier.

```python
import asyncio

from polars_baseball import statcast_single_game


async def main() -> None:
    game = await statcast_single_game(529429)
    print(game.head())


if __name__ == "__main__":
    asyncio.run(main())
```

## Example

```python
import asyncio

import polars_baseball as bp


async def main() -> None:
    single_day = await bp.statcast(start_date="2024-05-06", end_date="2024-05-06")
    two_days = await bp.statcast(start_date="2024-05-06", end_date="2024-05-07")
    dodgers = await bp.statcast(start_date="2024-05-06", end_date="2024-05-06", team="LAD")
    print(single_day.head())
    print(two_days.head())
    print(dodgers.head())


if __name__ == "__main__":
    asyncio.run(main())
```
