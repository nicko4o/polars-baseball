> [!NOTE]
> All public data-fetching APIs are asynchronous. Use `await` inside an async environment, or wrap calls with `asyncio.run()` in scripts.

# Statcast Running

Statcast running functions retrieve sprint-speed and 90-foot split leaderboards.
New code can call these through `polars_baseball.savant`, such as `pb.savant.sprint_speed(...)`.

## Functions

- `savant.sprint_speed(year: int, min_opp: int = 10) -> pl.DataFrame`
- `savant.running_splits(year: int, min_opp: int = 5, raw_splits: bool = True) -> pl.DataFrame`
- `savant.baserunning_run_value(year: int, min_opp: int = 5) -> pl.DataFrame`

## Arguments

- `year`: Leaderboard season.
- `min_opp`: Minimum number of sprinting opportunities.
- `raw_splits`: When `True`, return raw split times. When `False`, return split percentiles.

## Opportunity Definition

Statcast sprint opportunities include runs of at least two bases on non-home runs and home-to-first runs on topped or weakly hit balls.

## Example

```python
import asyncio

import polars_baseball as pb

async def main() -> None:
    speed = await pb.savant.sprint_speed(2019, min_opp=50)
    splits = await pb.savant.running_splits(2019, min_opp=50)
    percentiles = await pb.savant.running_splits(2019, min_opp=50, raw_splits=False)
    print(speed.head())
    print(splits.head())
    print(percentiles.head())

if __name__ == "__main__":
    asyncio.run(main())
```
