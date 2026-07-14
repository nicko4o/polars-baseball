> [!NOTE]
> 所有公開資料擷取 API 都是非同步函式。請在 async 環境中使用 `await`，或在指令碼中用 `asyncio.run()` 包裝呼叫。

# Retrosheet 資料擷取

Retrosheet 相關函式可查詢 game logs、賽程、名單、球場代碼與 event files。

## 函式

| 函式 | 資料 |
| --- | --- |
| `events(season, type="regular")` | 取得指定球季的 Retrosheet event 檔案，回傳檔名對應至 bytes 的 dict。 |
| `rosters(season)` | 球季名單資料。 |
| `schedules(season)` | 球季賽程。 |
| `season_game_logs(season)` | 例行賽 game logs。 |
| `all_star_game_logs()` | All-Star game logs。 |
| `wild_card_logs()` | Wild Card game logs。 |
| `division_series_logs()` | Division Series game logs。 |
| `lcs_logs()` | League Championship Series game logs。 |
| `world_series_logs()` | World Series game logs。 |
| `park_codes()` | Retrosheet 球場代碼。 |

## 範例

```python
import asyncio
from polars_baseball.apis.retrosheet import park_codes, rosters, schedules

async def main() -> None:
    roster_df = await rosters(2019)
    schedule_df = await schedules(2019)
    parks_df = await park_codes()
    print(roster_df.head())
    print(schedule_df.head())
    print(parks_df.head())

if __name__ == "__main__":
    asyncio.run(main())
```
