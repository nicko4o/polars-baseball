> [!NOTE]
> All public data-fetching APIs are asynchronous. Use `await` inside an async environment, or wrap calls with `asyncio.run()` in scripts.

# Baseball Reference Pitching WAR

`bwar_pitch(return_all: bool = False) -> pl.DataFrame`

Retrieves Baseball Reference WAR data from the `war_daily_pitch` table.

## Arguments

- `return_all`: When `True`, return all fields from `war_daily_pitch`. When `False`, return the standard subset used by common workflows.

## Example

```python
import asyncio
from polars_baseball.apis.bref import bwar_pitch

async def main() -> None:
    summary = await bwar_pitch()
    full_table = await bwar_pitch(return_all=True)
    print(summary.head())
    print(full_table.head())

if __name__ == "__main__":
    asyncio.run(main())
```
