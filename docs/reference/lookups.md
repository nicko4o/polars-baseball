> [!NOTE]
> All public data-fetching APIs (except `team_ids`) are asynchronous. Use `await` inside an async environment, or `asyncio.run()` in scripts.

# Lookups & Mappings

Resolves player IDs across MLBAM, Retrosheet, FanGraphs, and Baseball Reference (`KeyType`), and maps team IDs via `team_ids` (synchronous, backed by bundled CSV).

> [!NOTE]
> The first player lookup loads the register into memory. Call `client.lookup.reset()` to clear the in-memory table and reload fresh data on the next query.

## Example

```python
import asyncio
from polars_baseball import BaseballClient, KeyType


async def main() -> None:
    async with BaseballClient() as client:
        judge = await client.lookup.playerid_lookup("judge", "aaron")
        reversed_df = await client.lookup.playerid_reverse_lookup([592450], key_type=KeyType.MLBAM)
        teams_df = client.lookup.team_ids(2024)
        print(judge.head(1), reversed_df.head(1), teams_df.head(1))


if __name__ == "__main__":
    asyncio.run(main())
```

## Available Methods

`chadwick_register`, `get_lookup_table`, `player_name_suggestions`, `player_search_list`, `playerid_lookup`, `playerid_reverse_lookup`, `reset`, `team_ids`.

## API Reference

::: polars_baseball.lookup.LookupClient
