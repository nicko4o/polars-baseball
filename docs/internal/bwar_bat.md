> [!NOTE]
> All public data-fetching APIs are asynchronous. Use `await` inside an async environment, or wrap calls with `asyncio.run()` in scripts.

# Baseball Reference Batting WAR

`bwar_bat(return_all: bool = False) -> pl.DataFrame`

Retrieves Baseball Reference WAR data from the `war_daily_bat` table.

## Arguments

- `return_all`: When `True`, return all fields from `war_daily_bat`. When `False`, return the standard subset used by common workflows.

## Example

```python
import asyncio
from polars_baseball.apis.bref import bwar_bat

async def main() -> None:
    summary = await bwar_bat()
    full_table = await bwar_bat(return_all=True)
    print(summary.head())
    print(full_table.head())

if __name__ == "__main__":
    asyncio.run(main())
```
