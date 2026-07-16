> [!NOTE]
> 所有公開資料擷取 API 都是非同步函式。請在 async 環境中使用 `await`，或在指令碼中用 `asyncio.run()` 包裝呼叫。

# Player ID Reverse Lookup

`playerid_reverse_lookup(player_ids: list[int], key_type: KeyType = KeyType.MLBAM) -> pl.DataFrame`

用特定來源的 ID 清單反查球員資料。

## 參數

- `player_ids`：要查詢的 ID。
- `key_type`：ID 命名空間。MLBAM ID 使用 `KeyType.MLBAM`。

## 範例

```python
import asyncio
from polars_baseball import KeyType, playerid_reverse_lookup

async def main() -> None:
    players = await playerid_reverse_lookup([592450], key_type=KeyType.MLBAM)
    print(players.head())

if __name__ == "__main__":
    asyncio.run(main())
```
