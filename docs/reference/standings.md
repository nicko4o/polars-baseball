> [!NOTE]
> All public data-fetching APIs are asynchronous. Use `await` inside an async environment, or wrap calls with `asyncio.run()` in scripts.

# Standings

`standings(season: int | None = None) -> pl.DataFrame`

Retrieves one MLB standings table for a season, with division metadata columns.

## Arguments

- `season`: Season year. If omitted, the current season is requested.

## Example

```python
import asyncio
from polars_baseball import standings

async def main() -> None:
    df = await standings(2019)
    print(df.head())

if __name__ == "__main__":
    asyncio.run(main())
```
