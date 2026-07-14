> [!NOTE]
> 所有公開資料擷取 API 都是非同步函式。請在 async 環境中使用 `await`，或在指令碼中用 `asyncio.run()` 包裝呼叫。

# Lahman 資料擷取

Lahman 相關函式會從本地快取或 `POLARS_BASEBALL_DATASETS_URL` 讀取已編譯的 Parquet 表格。若未設定 compiled dataset root，Data Gateway 會從 upstream ZIP 編譯被請求的單一表格，並只將該表格以 Parquet 寫入快取。

## 資料表

| 函式 | 資料表 |
| --- | --- |
| `people()` | 球員基本資料與 ID。 |
| `parks()` | 球場 ID 與中繼資料。 |
| `all_star_full()` | All-Star 名單。 |
| `appearances()` | 球員依球隊、球季與守位彙整的出賽資料。 |
| `awards_managers()` | 總教練獎項。 |
| `awards_players()` | 球員獎項。 |
| `awards_share_managers()` | 總教練獎項投票占比。 |
| `awards_share_players()` | 球員獎項投票占比。 |
| `batting()` / `batting_post()` | 例行賽與季後賽打擊資料。 |
| `pitching()` / `pitching_post()` | 例行賽與季後賽投球資料。 |
| `fielding()` / `fielding_post()` | 例行賽與季後賽守備資料。 |
| `fielding_of()` / `fielding_of_split()` | 外野與外野 split 守備資料。 |
| `college_playing()` | 大學出賽紀錄。 |
| `hall_of_fame()` | 名人堂投票。 |
| `home_games()` | 主場比賽、觀眾與球場資料。 |
| `managers()` / `managers_half()` | 總教練戰績。 |
| `salaries()` | 薪資資料。 |
| `schools()` | 學校對照資料。 |
| `series_post()` | 季後賽系列賽結果。 |
| `teams_core()` / `teams_upstream()` / `teams_franchises()` / `teams_half()` | 球隊相關資料表。 |

## 範例

```python
import asyncio
from polars_baseball.apis.lahman import batting, download_lahman, people, teams_core

async def main() -> None:
    await download_lahman()  # 驗證並快取 upstream archive fallback
    people_df = await people()
    batting_df = await batting()
    teams_df = await teams_core()
    print(people_df.head())
    print(batting_df.head())
    print(teams_df.head())

if __name__ == "__main__":
    asyncio.run(main())
```
