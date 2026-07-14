> [!NOTE]
> 所有公開資料擷取 API 都是非同步函式。請在 async 環境中使用 `await`，或在指令碼中用 `asyncio.run()` 包裝呼叫。

# Statcast Single Game

`statcast_single_game(game_pk: str | int) -> pl.DataFrame`

查詢單場 MLB 比賽的 Statcast 資料。

## 參數

- `game_pk`：MLB Advanced Media game identifier。

## 範例

```python
import asyncio
from polars_baseball import statcast_single_game

async def main() -> None:
    game = await statcast_single_game(529429)
    print(game.head())

if __name__ == "__main__":
    asyncio.run(main())
```
