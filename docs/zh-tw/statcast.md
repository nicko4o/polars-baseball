> [!NOTE]
> 所有公開資料擷取 API 都是非同步函式。請在 async 環境中使用 `await`，或在指令碼中用 `asyncio.run()` 包裝呼叫。

# Statcast

`statcast(start_dt: str | None = None, end_dt: str | None = None, team: str | None = None, verbose: bool = True, parallel: bool = True) -> pl.DataFrame`

從 Baseball Savant 查詢指定日期區間的 pitch-level Statcast 資料。

## 回傳資料

以 `polars.DataFrame` 回傳，每列代表一球。Baseball Savant 的欄位說明見其 [CSV documentation](https://baseballsavant.mlb.com/csv-docs)。

## 參數

- `start_dt`：起始日期，格式為 `YYYY-MM-DD`。省略時使用昨天。
- `end_dt`：結束日期，格式為 `YYYY-MM-DD`。省略時只查詢 `start_dt`。
- `team`：選用球隊縮寫，例如 `BOS`、`SEA` 或 `NYY`。
- `verbose`：是否輸出進度資訊。
- `parallel`：大型日期區間查詢時，是否透過 event loop 並行請求。

## 資料可用性

Pitch-tracking Statcast 資料自 2008 年起可用。Launch speed 與 launch angle 類指標自 2015 年起可用。

## 範例

```python
import asyncio
import polars_baseball as bp

async def main() -> None:
    single_day = await bp.statcast("2017-07-04")
    week = await bp.statcast("2016-08-01", "2016-08-07")
    rangers = await bp.statcast("2016-04-01", "2016-10-30", team="TEX")
    yesterday = await bp.statcast()
    print(single_day.head())
    print(week.head())
    print(rangers.head())
    print(yesterday.head())

if __name__ == "__main__":
    asyncio.run(main())
```
