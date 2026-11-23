> [!NOTE]
> All public data-fetching APIs are asynchronous. Use `await` inside an async environment, or `asyncio.run()` in scripts.

# Retrosheet

Retrieves Retrosheet game logs, schedules, rosters, park codes, and raw event files. Schemas are defined in [`polars_baseball/_schemas/retrosheet.py`](https://github.com/nicko4o/polars-baseball/blob/main/polars_baseball/_schemas/retrosheet.py).

## Example

```python
import asyncio
from polars_baseball import BaseballClient


async def main() -> None:
    async with BaseballClient() as client:
        roster_df = await client.retrosheet.rosters(2019)
        parks_df = await client.retrosheet.park_codes()
        print(roster_df.head(), parks_df.head())


if __name__ == "__main__":
    asyncio.run(main())
```

## Available Methods

`all_star_game_logs`, `division_series_logs`, `events`, `lcs_logs`, `park_codes`, `rosters`, `schedules`, `season_game_logs`, `wild_card_logs`, `world_series_logs`.

## API Reference

::: polars_baseball.retrosheet.RetrosheetClient
