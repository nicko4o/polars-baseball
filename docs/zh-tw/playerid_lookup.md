> [!NOTE]
> 所有公開資料擷取 API 都是非同步函式。請在 async 環境中使用 `await`，或在指令碼中用 `asyncio.run()` 包裝呼叫。

# Player ID Lookup

`playerid_lookup(last: str, first: str | None = None, fuzzy: bool = False, ignore_accents: bool = False) -> pl.DataFrame`

`player_search_list(player_list: list[tuple[str, str]]) -> pl.DataFrame`

查詢 MLBAM、Retrosheet、FanGraphs、Baseball Reference 等來源的球員 ID。

## 參數

- `last`：球員姓氏。
- `first`：選用的名字。同時提供姓與名可縮小模糊結果。
- `fuzzy`：啟用 fuzzy matching。
- `ignore_accents`：比對前正規化重音字元。
- `player_list`：批次查詢用的 `(last, first)` tuple 清單。

## 範例

```python
import asyncio
from polars_baseball import playerid_lookup
from polars_baseball.apis.playerid import player_search_list

async def main() -> None:
    jones = await playerid_lookup("jones")
    chipper = await playerid_lookup("jones", "chipper")
    players = await player_search_list([
        ("brock", "lou"),
        ("jones", "chipper"),
    ])
    print(jones.head())
    print(chipper.head())
    print(players.head())

if __name__ == "__main__":
    asyncio.run(main())
```
