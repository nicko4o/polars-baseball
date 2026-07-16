> [!NOTE]
> 所有公開資料擷取 API 都是非同步函式。請在 async 環境中使用 `await`，或在指令碼中用 `asyncio.run()` 包裝呼叫。

# Prospect Rankings

`prospect_rankings(list_type: str = "top100", year: int | None = None, context: BaseballContext | None = None) -> pl.DataFrame`

查詢指定球季與類型的 MLB Pipeline 新秀排行榜。

---

## 參數

- `top_prospects(team_name: str | None = None, player_type: str | None = None)`：查詢指定球隊或全聯盟的 MLB top prospects。
  - `team_name`：不含空白的球隊名稱，例如 `bluejays` 或 `padres`。省略時回傳全聯盟 prospects。
  - `player_type`：`pitchers` 或 `batters`。省略時回傳兩者。
- `list_type`：要擷取的新秀榜單類型。預設為 `"top100"`。支援的選項包括：
  - `"top100"`：百大新秀總排名。
  - `"draft"`：選秀新秀排行。
  - `"international"`：國際新秀排行。
  - 守備位置代碼：`"c"`、`"1b"`、`"2b"`、`"3b"`、`"ss"`、`"of"`、`"rhp"`、`"lhp"`。
  - 球隊名稱：查詢特定球隊的前 30 大新秀（例如 `"yankees"`、`"redsox"`、`"dbacks"`）。
- `year`：歷史年份（選填）。若未指定，則查詢當前最新的排行榜。
- `context`：選擇性的依賴注入 context。

---

## 範例

### 1. 查詢百大新秀

```python
import asyncio
from polars_baseball import prospect_rankings

async def main() -> None:
    df = await prospect_rankings("top100")
    print(df.head(5))

if __name__ == "__main__":
    asyncio.run(main())
```

### 2. 查詢球隊或全聯盟 Top Prospects

```python
import asyncio

from polars_baseball import top_prospects


async def main() -> None:
    blue_jays_pitchers = await top_prospects("bluejays", "pitchers")
    leaguewide = await top_prospects()
    print(blue_jays_pitchers.head())
    print(leaguewide.head())


if __name__ == "__main__":
    asyncio.run(main())
```

### 3. 查詢特定球隊的前 30 大新秀

```python
import asyncio
from polars_baseball import prospect_rankings

async def main() -> None:
    df = await prospect_rankings("yankees")
    print(df.head(5))

if __name__ == "__main__":
    asyncio.run(main())
```
