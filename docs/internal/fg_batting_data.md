> [!NOTE]
> All public data-fetching APIs are asynchronous. Use `await` inside an async environment, or wrap calls with `asyncio.run()` in scripts.

# FanGraphs Batting Data

`fg_data(request: FanGraphsRequest) -> pl.DataFrame`

Retrieves season-level FanGraphs batting statistics. Use `FanGraphsRequest.batting()` to construct the request.

## Returned Data

Returns a `polars.DataFrame`.

## Key Arguments (via `FanGraphsRequest.batting()`)

- `start_season`: First season to retrieve.
- `end_season`: Final season to retrieve. Omit or set `None` to use `start_season`.
- `qual`: Minimum plate appearances. `None` uses the FanGraphs default.
- `split_seasons`: `True` returns one row per player per season. `False` returns aggregate rows over the requested seasons.
- `team`, `position`, `league`, `month`: Optional filters (supports strings like `"AL"`).
- `stat_columns`: Columns to request, or `ALL` for the default set.

## Example

```python
import asyncio
import polars_baseball as bp

async def main() -> None:
    season = await bp.fg_data(bp.FanGraphsRequest.batting(start_season=2024))
    qualified = await bp.fg_data(bp.FanGraphsRequest.batting(start_season=2023, qual=50))
    split = await bp.fg_data(bp.FanGraphsRequest.batting(start_season=2020, end_season=2024, split_seasons=True))
    aggregate = await bp.fg_data(bp.FanGraphsRequest.batting(start_season=2020, end_season=2024, split_seasons=False))
    print(season.head())
    print(qualified.head())
    print(split.head())
    print(aggregate.head())

if __name__ == "__main__":
    asyncio.run(main())
```
