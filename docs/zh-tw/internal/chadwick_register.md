> [!NOTE]
> 所有公開資料擷取 API 都是非同步函式。請在 async 環境中使用 `await`，或在指令碼中用 `asyncio.run()` 包裝呼叫。

# Chadwick Register

`chadwick_register(save: bool = True) -> pl.DataFrame`

查詢 Chadwick Register people table。此表包含棒球相關識別碼，也可能包含非 MLB 球員的人員。

## 參數

- `save`：是否將編譯後的 register Parquet 表格快取到磁碟。設為 `False` 時會執行不寫入快取的邊界讀取。

## 範例

```python
import asyncio
from polars_baseball.apis.playerid import chadwick_register

async def main() -> None:
    register = await chadwick_register()
    saved_register = await chadwick_register(save=True)
    print(register.head())
    print(saved_register.head())

if __name__ == "__main__":
    asyncio.run(main())
```
