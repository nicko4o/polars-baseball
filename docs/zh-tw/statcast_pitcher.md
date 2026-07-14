> [!NOTE]
> 所有公開資料擷取 API 都是非同步函式。請在 async 環境中使用 `await`，或在指令碼中用 `asyncio.run()` 包裝呼叫。

# Statcast 投手排行榜

這些函式會以 `polars.DataFrame` 回傳 Baseball Savant 的球員排行榜與 pitch-level 資料。

## 函式

| 函式 | 資料 |
| --- | --- |
| `statcast_pitcher` | 指定投手與日期區間的 pitch-level Statcast 資料。 |
| `statcast_pitcher_exitvelo_barrels` | 投手被擊球品質資料。 |
| `statcast_pitcher_expected_stats` | 投手被預期表現資料。 |
| `statcast_pitcher_pitch_arsenal` | 投手球種 arsenal 高階資料。 |
| `statcast_pitcher_arsenal_stats` | 依球種 arsenal 彙整的結果指標。 |
| `statcast_pitcher_pitch_movement` | 依球種統計的位移資料。 |
| `statcast_pitcher_active_spin` | Active spin 指標。 |
| `statcast_pitcher_percentile_ranks` | 投手百分位排名。 |
| `statcast_pitcher_spin_dir_comp` | 不同球種之間的 spin direction 比較。 |
| `statcast_pitcher_run_value` | Run value 排行榜資料。 |
| `statcast_pitcher_bat_tracking` | 面對投手的 bat-tracking 資料。 |

## 常用參數

- `year`：排行榜球季。
- `start_dt` / `end_dt`：pitch-level 函式使用的日期區間。
- `player_id`：pitch-level 球員查詢使用的 MLBAM player ID。
- `minPA`、`minP`、`minBBE`、`minSwings`：最低打席、投球數或事件門檻。部分函式接受 `'q'` 表示合格球員。

## 資料可用性

Pitch-level Statcast 自 2008 年起可用。擊球初速與 launch angle 等擊球品質指標自 2015 年起可用。

## 範例

```python
import asyncio
from polars_baseball import statcast_pitcher
from polars_baseball.apis.savant_leaderboards import statcast_pitcher_pitch_arsenal

async def main() -> None:
    pitches = await statcast_pitcher("2024-05-06", "2024-05-06", player_id=506433)
    arsenal = await statcast_pitcher_pitch_arsenal(2024, minP=250)
    print(pitches.head())
    print(arsenal.head())

if __name__ == "__main__":
    asyncio.run(main())
```
