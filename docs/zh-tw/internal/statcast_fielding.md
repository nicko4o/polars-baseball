> [!NOTE]
> 所有公開資料擷取 API 都是非同步函式。請在 async 環境中使用 `await`，或在指令碼中用 `asyncio.run()` 包裝呼叫。

# Statcast Fielding

Statcast fielding 函式會查詢 Baseball Savant 守備排行榜。

## 函式

| 函式 | 資料 |
| --- | --- |
| `statcast_outs_above_average(year, pos, min_att="q", view="Fielder")` | Outs Above Average。 |
| `statcast_fielding_run_value(year, pos, min_inn=100)` | Fielding run value。 |
| `statcast_outfield_directional_oaa(year, min_opp="q")` | Directional outfield OAA。 |
| `statcast_outfield_catch_prob(year, min_opp="q")` | Outfield catch probability。 |
| `statcast_outfielder_jump(year, min_att="q")` | Outfielder jump metrics。 |
| `statcast_catcher_poptime(year, min_2b_att=5, min_3b_att=0)` | Catcher pop time。 |
| `statcast_catcher_framing(year, min_called_p="q")` | Catcher framing。 |
| `statcast_arm_strength(year, min_throws=50)` | Fielder arm strength。 |
| `statcast_catcher_throwing(year, min_att=5)` | Catcher throwing run value。 |
| `statcast_catcher_stance(year)` | Catcher stance setup metrics。 |

## 範例

```python
import asyncio
from polars_baseball.apis.savant_fielding_running import statcast_catcher_framing, statcast_outs_above_average

async def main() -> None:
    oaa = await statcast_outs_above_average(2024, pos="CF", min_att="q")
    framing = await statcast_catcher_framing(2024, min_called_p="q")
    print(oaa.head())
    print(framing.head())

if __name__ == "__main__":
    asyncio.run(main())
```
