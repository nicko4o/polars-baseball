> [!NOTE]
> All public data-fetching APIs are asynchronous. Use `await` inside an async environment, or wrap calls with `asyncio.run()` in scripts.

# Standings

`standings(season: int | None = None) -> list[pl.DataFrame]`

Retrieves MLB standings tables for a season.

## Arguments

- `season`: Season year. If omitted, the current season is requested.

## Example

```python
import asyncio
from polars_baseball import standings

async def main() -> None:
    divisions = await standings(2019)
    for division in divisions:
        print(division.head())

if __name__ == "__main__":
    asyncio.run(main())
```
