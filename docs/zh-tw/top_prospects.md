> [!NOTE]
> 所有公開資料擷取 API 都是非同步函式。請在 async 環境中使用 `await`，或在指令碼中用 `asyncio.run()` 包裝呼叫。

# Top Prospects

`top_prospects(team_name: str | None = None, player_type: str | None = None) -> pl.DataFrame`

查詢指定球隊或全聯盟的 MLB top prospects。

## 參數

- `team_name`：不含空白的球隊名稱，例如 `bluejays` 或 `padres`。省略時回傳全聯盟 prospects。
- `player_type`：`pitchers` 或 `batters`。省略時回傳兩者。

## 範例

```python
import asyncio
from polars_baseball import top_prospects

async def main() -> None:
    blue_jays_pitchers = await top_prospects("bluejays", "pitchers")
    leaguewide = await top_prospects()
    leaguewide_batters = await top_prospects(None, "batters")
    padres = await top_prospects("padres")
    print(blue_jays_pitchers.head())
    print(leaguewide.head())
    print(leaguewide_batters.head())
    print(padres.head())

if __name__ == "__main__":
    asyncio.run(main())
```
