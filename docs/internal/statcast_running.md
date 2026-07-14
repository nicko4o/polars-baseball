> [!NOTE]
> All public data-fetching APIs are asynchronous. Use `await` inside an async environment, or wrap calls with `asyncio.run()` in scripts.

# Statcast Running

Statcast running functions retrieve sprint-speed and 90-foot split leaderboards.

## Functions

- `statcast_sprint_speed(year: int, min_opp: int = 10) -> pl.DataFrame`
- `statcast_running_splits(year: int, min_opp: int = 5, raw_splits: bool = True) -> pl.DataFrame`
- `statcast_baserunning_run_value(year: int, min_opp: int = 5) -> pl.DataFrame`

## Arguments

- `year`: Leaderboard season.
- `min_opp`: Minimum number of sprinting opportunities.
- `raw_splits`: When `True`, return raw split times. When `False`, return split percentiles.

## Opportunity Definition

Statcast sprint opportunities include runs of at least two bases on non-home runs and home-to-first runs on topped or weakly hit balls.

## Example

```python
import asyncio
from polars_baseball.apis.savant_fielding_running import statcast_running_splits, statcast_sprint_speed

async def main() -> None:
    speed = await statcast_sprint_speed(2019, min_opp=50)
    splits = await statcast_running_splits(2019, min_opp=50)
    percentiles = await statcast_running_splits(2019, min_opp=50, raw_splits=False)
    print(speed.head())
    print(splits.head())
    print(percentiles.head())

if __name__ == "__main__":
    asyncio.run(main())
```
