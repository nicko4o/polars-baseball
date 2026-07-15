> [!NOTE]
> 所有公開資料擷取 API 都是非同步函式。請在 async 環境中使用 `await`，或在指令碼中用 `asyncio.run()` 包裝呼叫。

# Statcast 打者排行榜

這些函式會以 `polars.DataFrame` 回傳 Baseball Savant 的球員排行榜與 pitch-level 資料。

## 函式

| 函式 | 資料 |
| --- | --- |
| `statcast_batter` | 指定打者與日期區間的 pitch-level Statcast 資料。 |
| `statcast_batter_exitvelo_barrels` | 擊球初速與 barrel 相關指標。 |
| `statcast_batter_expected_stats` | 基於擊球品質的 expected stats。 |
| `statcast_batter_percentile_ranks` | 合格打者的百分位排名。 |
| `statcast_batter_pitch_arsenal` | 打者面對的球種 arsenal 資料。 |
| `statcast_batter_run_value` | Run value 排行榜資料。 |
| `statcast_batter_bat_tracking` | Bat-tracking 排行榜資料。 |

## 常用參數

- `year`：排行榜球季。
- `start_date` / `end_date`：pitch-level 函式使用的日期區間。
- `player_id`：pitch-level 球員查詢使用的 MLBAM player ID。
- `minPA`、`minP`、`minBBE`、`minSwings`：最低打席、投球數或事件門檻。部分函式接受 `'q'` 表示合格球員。

## 資料可用性

Pitch-level Statcast 自 2008 年起可用。擊球初速與 launch angle 等擊球品質指標自 2015 年起可用。

## 範例

```python
import asyncio
from polars_baseball import statcast_batter
from polars_baseball.apis.savant_leaderboards import statcast_batter_expected_stats

async def main() -> None:
    pitches = await statcast_batter(start_date="2024-05-06", end_date="2024-05-06", player_id=660271)
    expected = await statcast_batter_expected_stats(2024, minPA=100)
    print(pitches.head())
    print(expected.head())

if __name__ == "__main__":
    asyncio.run(main())
```
