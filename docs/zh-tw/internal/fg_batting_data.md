> [!NOTE]
> 所有公開資料擷取 API 都是非同步函式。請在 async 環境中使用 `await`，或在指令碼中用 `asyncio.run()` 包裝呼叫。

# FanGraphs 打擊資料

`fg_data(request: FanGraphsRequest) -> pl.DataFrame`

查詢 FanGraphs 的球季層級打擊統計。使用 `FanGraphsRequest.batting()` 建立請求。

## 回傳資料

回傳 `polars.DataFrame`。

## 主要參數（透過 `FanGraphsRequest.batting()`）

- `start_season`：起始球季。
- `end_season`：結束球季。省略或設為 `None` 以使用 `start_season`。
- `qual`：最低打席數門檻。`None` 使用 FanGraphs 預設門檻。
- `split_seasons`：`True` 回傳每位球員逐季資料；`False` 回傳查詢區間的彙總列。
- `team`、`position`、`league`、`month`：選用篩選條件（支援字串如 `"AL"`）。
- `stat_columns`：要請求的欄位，或用 `ALL` 取得預設欄位。

## 範例

```python
import asyncio
import polars_baseball as bp

async def main() -> None:
    season = await bp.fg_data(bp.FanGraphsRequest.batting(2024))
    qualified = await bp.fg_data(bp.FanGraphsRequest.batting(2023, qual=50))
    split = await bp.fg_data(bp.FanGraphsRequest.batting(2020, end_season=2024, split_seasons=True))
    aggregate = await bp.fg_data(bp.FanGraphsRequest.batting(2020, end_season=2024, split_seasons=False))
    print(season.head())
    print(qualified.head())
    print(split.head())
    print(aggregate.head())

if __name__ == "__main__":
    asyncio.run(main())
```
