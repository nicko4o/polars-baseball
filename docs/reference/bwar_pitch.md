> [!NOTE]
> All public data-fetching APIs are asynchronous. Use `await` inside an async environment, or wrap calls with `asyncio.run()` in scripts.

# Baseball Reference Pitching WAR

`bwar_pitch(return_all: bool = False) -> pl.DataFrame`

Retrieves Baseball Reference WAR data from the `war_daily_pitch` table.

## Arguments

- `return_all`: When `True`, return all fields from `war_daily_pitch`. When `False`, return the standard subset used by common workflows.

## Live-data limitation

Baseball Reference currently returns HTTP 403 for this endpoint in live verification, so this page intentionally omits a guaranteed non-empty executable example.
