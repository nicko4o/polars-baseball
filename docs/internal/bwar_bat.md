> [!NOTE]
> All public data-fetching APIs are asynchronous. Use `await` inside an async environment, or wrap calls with `asyncio.run()` in scripts.

# Baseball Reference Batting WAR

`bwar_bat(return_all: bool = False) -> pl.DataFrame`

Retrieves Baseball Reference WAR data from the `war_daily_bat` table.

## Arguments

- `return_all`: When `True`, return all fields from `war_daily_bat`. When `False`, return the standard subset used by common workflows.

## Live-data limitation

Baseball Reference currently returns HTTP 403 for this endpoint in live verification, so this page intentionally omits a guaranteed non-empty executable example.
