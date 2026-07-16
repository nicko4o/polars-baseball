> [!NOTE]
> All public data-fetching APIs are asynchronous. Use `await` inside an async environment, or wrap calls with `asyncio.run()` in scripts.

# Statcast Fielding

Statcast fielding functions retrieve Baseball Savant fielding leaderboards.
New code can call these through `polars_baseball.savant`, such as `pb.savant.outs_above_average(...)`.

## Functions

| Function | Data |
| --- | --- |
| `savant.outs_above_average(year, pos, min_att="q", view="Fielder")` | Outs Above Average. |
| `savant.fielding_run_value(year, pos, min_inn=100)` | Fielding run value. |
| `savant.outfield_directional_oaa(year, min_opp="q")` | Directional outfield OAA. |
| `savant.outfield_catch_prob(year, min_opp="q")` | Outfield catch probability. |
| `savant.outfielder_jump(year, min_att="q")` | Outfielder jump metrics. |
| `savant.catcher_poptime(year, min_2b_att=5, min_3b_att=0)` | Catcher pop time. |
| `savant.catcher_framing(year, min_called_p="q")` | Catcher framing. |
| `savant.arm_strength(year, min_throws=50)` | Fielder arm strength. |
| `savant.catcher_throwing(year, min_att=5)` | Catcher throwing run value. |
| `savant.catcher_stance(year)` | Catcher stance setup metrics. |

## Example

```python
import asyncio

import polars_baseball as pb

async def main() -> None:
    oaa = await pb.savant.outs_above_average(2024, pos="CF", min_att="q")
    framing = await pb.savant.catcher_framing(2024, min_called_p="q")
    print(oaa.head())
    print(framing.head())

if __name__ == "__main__":
    asyncio.run(main())
```
