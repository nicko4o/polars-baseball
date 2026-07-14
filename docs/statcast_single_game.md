> [!NOTE]
> All public data-fetching APIs are asynchronous. Use `await` inside an async environment, or wrap calls with `asyncio.run()` in scripts.

# Statcast Single Game

`statcast_single_game(game_pk: str | int) -> pl.DataFrame`

Retrieves Statcast data for one MLB game.

## Arguments

- `game_pk`: MLB Advanced Media game identifier.

## Example

```python
import asyncio
from polars_baseball import statcast_single_game

async def main() -> None:
    game = await statcast_single_game(529429)
    print(game.head())

if __name__ == "__main__":
    asyncio.run(main())
```
