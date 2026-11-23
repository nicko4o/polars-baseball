> [!NOTE]
> All public data-fetching APIs are asynchronous. Use `await` inside an async environment, or `asyncio.run()` in scripts.

# Baseball Reference

Retrieves daily WAR (`bwar_bat`, `bwar_pitch`), single-season `game_logs`, and `splits` from Baseball Reference.

> [!WARNING]
> Baseball Reference enforces strict rate limits and Cloudflare Turnstile anti-bot protection. Configure `bref_requests_per_minute` on `HttpClient`, pass clearance cookies via `extra_headers`, or rely on local Parquet caching.

## Example

```python
import asyncio
from polars_baseball import BaseballClient


async def main() -> None:
    async with BaseballClient() as client:
        batting_war = await client.bref.bwar_bat(all_columns=False)
        print(batting_war.head())


if __name__ == "__main__":
    asyncio.run(main())
```

## API Reference

::: polars_baseball.bref.BRefClient
