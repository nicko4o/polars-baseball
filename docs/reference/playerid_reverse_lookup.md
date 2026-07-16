> [!NOTE]
> All public data-fetching APIs are asynchronous. Use `await` inside an async environment, or wrap calls with `asyncio.run()` in scripts.

# Player ID Reverse Lookup

`playerid_reverse_lookup(player_ids: list[int], key_type: KeyType = KeyType.MLBAM) -> pl.DataFrame`

Finds player records from a list of source-specific IDs.

## Arguments

- `player_ids`: IDs to search for.
- `key_type`: ID namespace. Use `KeyType.MLBAM` for MLBAM IDs.

## Example

```python
import asyncio
from polars_baseball import KeyType, playerid_reverse_lookup

async def main() -> None:
    players = await playerid_reverse_lookup([592450], key_type=KeyType.MLBAM)
    print(players.head())

if __name__ == "__main__":
    asyncio.run(main())
```
