> [!NOTE]
> All public data-fetching APIs are asynchronous. Use `await` inside an async environment, or `asyncio.run()` in scripts.

# FanGraphs

Retrieves player and team leaderboards (`batting`, `pitching`, `fielding`, `team_*`, `season_schedule`, `fg_data`) from FanGraphs.

## Leaderboard Filtering (`filters`)

Pass conditions as 3-tuples or `FanGraphsFilter` objects (`>`, `>=`, `<`, `<=`, `==`/`=`, `!=`):

```python
import polars_baseball as pb

filters_tuple = [("HR", ">", 40), ("AVG", ">=", 0.300)]
filters_factory = [pb.fangraphs.FanGraphsFilter.gt("HR", 40)]
filters_enum = [pb.fangraphs.FanGraphsFilter("HR", pb.fangraphs.FanGraphsFilterOp.GT, 40)]
```

## Example

```python
import asyncio
from polars_baseball import BaseballClient


async def main() -> None:
    async with BaseballClient() as client:
        df = await client.fangraphs.batting(
            start_season=2024,
            filters=[("HR", ">", 40), ("AVG", ">=", 0.300)],
        )
        print(df.head())


if __name__ == "__main__":
    asyncio.run(main())
```

## Available Methods

`batting`, `fg_data`, `fielding`, `pitching`, `season_schedule`, `team_batting`, `team_fielding`, `team_pitching`, `team_relievers`, `team_starters`.

## API Reference

::: polars_baseball.fangraphs.FanGraphsClient
