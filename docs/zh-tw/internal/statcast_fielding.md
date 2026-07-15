> [!NOTE]
> 所有公開資料擷取 API 都是非同步函式。請在 async 環境中使用 `await`，或在指令碼中用 `asyncio.run()` 包裝呼叫。

# Statcast Fielding

Statcast fielding 函式會查詢 Baseball Savant 守備排行榜。新程式碼可透過 `polars_baseball.savant` 呼叫，例如 `pb.savant.outs_above_average(...)`。

## 函式

| 函式 | 資料 |
| --- | --- |
| `savant.outs_above_average(year, pos, min_att="q", view="Fielder")` | Outs Above Average。 |
| `savant.fielding_run_value(year, pos, min_inn=100)` | Fielding run value。 |
| `savant.outfield_directional_oaa(year, min_opp="q")` | Directional outfield OAA。 |
| `savant.outfield_catch_prob(year, min_opp="q")` | Outfield catch probability。 |
| `savant.outfielder_jump(year, min_att="q")` | Outfielder jump metrics。 |
| `savant.catcher_poptime(year, min_2b_att=5, min_3b_att=0)` | Catcher pop time。 |
| `savant.catcher_framing(year, min_called_p="q")` | Catcher framing。 |
| `savant.arm_strength(year, min_throws=50)` | Fielder arm strength。 |
| `savant.catcher_throwing(year, min_att=5)` | Catcher throwing run value。 |
| `savant.catcher_stance(year)` | Catcher stance setup metrics。 |

既有 `statcast_*` root 函式仍會保留支援。

## 範例

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
