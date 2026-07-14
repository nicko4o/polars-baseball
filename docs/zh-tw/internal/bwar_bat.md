> [!NOTE]
> 所有公開資料擷取 API 都是非同步函式。請在 async 環境中使用 `await`，或在指令碼中用 `asyncio.run()` 包裝呼叫。

# Baseball Reference 打擊 WAR

`bwar_bat(return_all: bool = False) -> pl.DataFrame`

從 Baseball Reference 的 `war_daily_bat` 表查詢 打擊 WAR 資料。

## 參數

- `return_all`：`True` 時回傳 `war_daily_bat` 的所有欄位；`False` 時回傳常用工作流需要的標準欄位子集。

## 範例

```python
import asyncio
from polars_baseball.apis.bref import bwar_bat

async def main() -> None:
    summary = await bwar_bat()
    full_table = await bwar_bat(return_all=True)
    print(summary.head())
    print(full_table.head())

if __name__ == "__main__":
    asyncio.run(main())
```
