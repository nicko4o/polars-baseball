> [!NOTE]
> All public data-fetching APIs are asynchronous. Use `await` inside an async environment, or wrap calls with `asyncio.run()` in scripts.

# Player ID Lookup

`playerid_lookup(last: str, first: str | None = None, fuzzy: bool = False, ignore_accents: bool = False) -> pl.DataFrame`

`player_search_list(player_list: list[tuple[str, str]]) -> pl.DataFrame`

Looks up player IDs across MLBAM, Retrosheet, FanGraphs, Baseball Reference, and related sources.

## Arguments

- `last`: Player last name.
- `first`: Optional first name. Supplying both names narrows ambiguous results.
- `fuzzy`: Enable fuzzy matching.
- `ignore_accents`: Normalize accented characters before matching.
- `player_list`: A list of `(last, first)` tuples for batch lookup.

## Example

```python
import asyncio
from polars_baseball import playerid_lookup
from polars_baseball.apis.playerid import player_search_list

async def main() -> None:
    jones = await playerid_lookup("jones")
    chipper = await playerid_lookup("jones", "chipper")
    players = await player_search_list([
        ("brock", "lou"),
        ("jones", "chipper"),
    ])
    print(jones.head())
    print(chipper.head())
    print(players.head())

if __name__ == "__main__":
    asyncio.run(main())
```
