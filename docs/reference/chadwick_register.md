> [!NOTE]
> All public data-fetching APIs are asynchronous. Use `await` inside an async environment, or wrap calls with `asyncio.run()` in scripts.

# Chadwick Register

`chadwick_register(save: bool = True) -> pl.DataFrame`

Retrieves the Chadwick Register people table. The table contains baseball identifiers and can include people who are not MLB players.

## Arguments

- `save`: Cache the compiled register Parquet table to disk. Set `False` for an uncached boundary read.

## Example

```python
import asyncio
from polars_baseball import chadwick_register

async def main() -> None:
    register = await chadwick_register()
    saved_register = await chadwick_register(save=True)
    print(register.head())
    print(saved_register.head())

if __name__ == "__main__":
    asyncio.run(main())
```
