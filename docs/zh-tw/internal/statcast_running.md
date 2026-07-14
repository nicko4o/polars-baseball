> [!NOTE]
> 所有公開資料擷取 API 都是非同步函式。請在 async 環境中使用 `await`，或在指令碼中用 `asyncio.run()` 包裝呼叫。

# Statcast Running

Statcast running 函式會查詢 sprint speed 與 90-foot split 排行榜。

## 函式

- `statcast_sprint_speed(year: int, min_opp: int = 10) -> pl.DataFrame`
- `statcast_running_splits(year: int, min_opp: int = 5, raw_splits: bool = True) -> pl.DataFrame`
- `statcast_baserunning_run_value(year: int, min_opp: int = 5) -> pl.DataFrame`

## 參數

- `year`：排行榜球季。
- `min_opp`：最低 sprinting opportunities 數量。
- `raw_splits`：`True` 回傳原始 split times；`False` 回傳 split percentiles。

## Opportunity 定義

Statcast sprint opportunities 包含非全壘打時跑兩個壘包以上，以及 topped 或 weakly hit balls 的本壘到一壘跑壘。

## 範例

```python
import asyncio
from polars_baseball.apis.savant_fielding_running import statcast_running_splits, statcast_sprint_speed

async def main() -> None:
    speed = await statcast_sprint_speed(2019, min_opp=50)
    splits = await statcast_running_splits(2019, min_opp=50)
    percentiles = await statcast_running_splits(2019, min_opp=100, raw_splits=False)
    print(speed.head())
    print(splits.head())
    print(percentiles.head())

if __name__ == "__main__":
    asyncio.run(main())
```
