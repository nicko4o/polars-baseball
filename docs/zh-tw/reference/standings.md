> [!NOTE]
> 所有公開資料擷取 API 都是非同步函式。請在 async 環境中使用 `await`，或在指令碼中用 `asyncio.run()` 包裝呼叫。

# Standings

`standings(season: int | None = None) -> pl.DataFrame`

查詢指定球季的單一 MLB standings table，並包含 division metadata 欄位。

## 參數

- `season`：球季年份。省略時查詢目前球季。

## 範例

```python
import asyncio
from polars_baseball import standings

async def main() -> None:
    df = await standings(2019)
    print(df.head())

if __name__ == "__main__":
    asyncio.run(main())
```
