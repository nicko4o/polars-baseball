> [!NOTE]
> All public data-fetching APIs are asynchronous. Use `await` inside an async environment, or wrap calls with `asyncio.run()` in scripts.

# Statcast

`statcast(start_dt: str | None = None, end_dt: str | None = None, team: str | None = None, verbose: bool = True, parallel: bool = True) -> pl.DataFrame`

Retrieves pitch-level Statcast data from Baseball Savant for a date range.

## Returned Data

Returns one row per pitch as a `polars.DataFrame`. Baseball Savant documents the CSV columns in its [CSV documentation](https://baseballsavant.mlb.com/csv-docs).

## Arguments

- `start_dt`: First date in `YYYY-MM-DD` format. If omitted, yesterday is used.
- `end_dt`: Last date in `YYYY-MM-DD` format. If omitted, only `start_dt` is queried.
- `team`: Optional team abbreviation such as `BOS`, `SEA`, or `NYY`.
- `verbose`: Print progress output.
- `parallel`: Run large date-range requests concurrently with the event loop.

## Data Availability

Pitch-tracking Statcast data starts in 2008. Launch-speed and launch-angle metrics are available from 2015 onward.

## Example

```python
import asyncio
import polars_baseball as bp

async def main() -> None:
    single_day = await bp.statcast("2017-07-04")
    week = await bp.statcast("2016-08-01", "2016-08-07")
    rangers = await bp.statcast("2016-04-01", "2016-10-30", team="TEX")
    yesterday = await bp.statcast()
    print(single_day.head())
    print(week.head())
    print(rangers.head())
    print(yesterday.head())

if __name__ == "__main__":
    asyncio.run(main())
```
