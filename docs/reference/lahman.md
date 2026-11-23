> [!NOTE]
> All public data-fetching APIs are asynchronous. Use `await` inside an async environment, or `asyncio.run()` in scripts.

# Lahman

Retrieves compiled Parquet tables from local cache or `POLARS_BASEBALL_DATASETS_URL`. When no compiled dataset root is configured, the gateway downloads and compiles the requested table from the upstream ZIP archive.

## Example

```python
import asyncio
from polars_baseball import BaseballClient


async def main() -> None:
    async with BaseballClient() as client:
        batting_df = await client.lahman.batting()
        print(batting_df.head())


if __name__ == "__main__":
    asyncio.run(main())
```

## Available Methods

`all_star_full`, `appearances`, `awards_managers`, `awards_players`, `awards_share_managers`, `awards_share_players`, `batting`, `batting_post`, `college_playing`, `download_lahman`, `fielding`, `fielding_of`, `fielding_of_split`, `fielding_post`, `hall_of_fame`, `home_games`, `managers`, `managers_half`, `parks`, `people`, `pitching`, `pitching_post`, `salaries`, `schools`, `series_post`, `teams_core`, `teams_franchises`, `teams_half`, `teams_upstream`.

## API Reference

::: polars_baseball.lahman.LahmanClient
