> [!NOTE]
> 所有公開資料擷取 API 都是非同步函式。請在 async 環境中使用 `await`，或在指令碼中用 `asyncio.run()` 包裝呼叫。

# MLB Stats API

適用情境：查官方 MLB endpoint 資料，例如賽程、名冊、game feed、boxscore、交易或 metadata。
不適用情境：需要 FanGraphs leaderboard、Lahman 歷史表，或 Baseball Savant pitch-level search。
回傳粒度：依 endpoint 而定，例如比賽、人員、名冊、play、局數或維度資料列。
資料來源：MLB Stats API。

提供官方 MLB Stats API 端點 (`statsapi.mlb.com`) 的存取，用以查詢球員、賽程、球隊、名冊、比賽資料與排行榜。
新程式碼可使用較短的 `polars_baseball.mlb` namespace，例如 `pb.mlb.schedule(...)`。

## API 分類

| 分類 | APIs | 適用情境 |
| --- | --- | --- |
| Identity | `mlb.people`, `mlb.people_awards` | 查官方人物 metadata 或獎項時間線。 |
| 賽程與球隊 metadata | `mlb.schedule`, `mlb.teams`, `mlb.roster`, `mlb.venues`, `mlb.divisions`, `mlb.leagues` | 查比賽列表、名冊 snapshot 或可 join 的維度表。 |
| 比賽資料 | `mlb.game_boxscore`, `mlb.game_boxscore_stats`, `mlb.game_play_by_play`, `mlb.game_win_probability`, `mlb.game_feed_live`, `mlb.game_linescore` | 查單場球員、play、live feed 或局數資料。 |
| 統計與排行榜 | `mlb.player_stats`, `mlb.team_stats`, `mlb.stat_leaders`, `mlb.pitch_arsenal`, `standings` | 查官方 stat groups、league leaders 或戰績表。 |
| Operations | `mlb.transactions`, `mlb.draft`, `mlb.postseason_schedule` | 查球員異動、選秀或季後賽賽程列。 |

## 1. 球員基本資料 (`mlb.people`)

`mlb.people(person_ids: list[int] | int, force_update: bool = False, context: BaseballContext | None = None) -> pl.DataFrame`

查詢一或多位球員的基本資料。

```python
import asyncio

import polars_baseball as pb

async def main() -> None:
    df = await pb.mlb.people(450314)
    print(df.select(["id", "fullName", "currentAge", "mlbDebutDate"]))

if __name__ == "__main__":
    asyncio.run(main())
```

## 2. 球隊名冊 (`mlb.roster`)

`mlb.roster(team_id: int, season: int | None = None, roster_type: str = "active", force_update: bool = False, context: BaseballContext | None = None) -> pl.DataFrame`

查詢指定球隊與球季的名冊。

```python
import asyncio

import polars_baseball as pb

async def main() -> None:
    df = await pb.mlb.roster(121, season=2024)
    print(df.select(["personId", "fullName", "jerseyNumber", "positionName"]))

if __name__ == "__main__":
    asyncio.run(main())
```

## 3. 賽程 (`mlb.schedule`)

`mlb.schedule(season: int | None = None, date: str | None = None, team_id: int | None = None, hydrate: str | None = None, force_update: bool = False, context: BaseballContext | None = None) -> pl.DataFrame`

依球季、日期或球隊查詢 MLB 賽程。

```python
import asyncio

import polars_baseball as pb

async def main() -> None:
    df = await pb.mlb.schedule(date="2024-05-06")
    print(df.select(["gamePk", "gameDate", "awayTeamName", "homeTeamName"]))

if __name__ == "__main__":
    asyncio.run(main())
```

## 4. 球員統計 (`mlb.player_stats`)

`mlb.player_stats(person_id: int, group: str, stats_type: str = "season", season: int | None = None, force_update: bool = False, context: BaseballContext | None = None) -> pl.DataFrame`

查詢球員打擊、投球或守備統計。

```python
import asyncio
import polars_baseball as pb

async def main() -> None:
    df = await pb.mlb.player_stats(660271, group="hitting", stats_type="gameLog", season=2024)
    print(df.select(["season", "group", "statType", "gamesPlayed", "homeRuns"]))

if __name__ == "__main__":
    asyncio.run(main())
```

## 5. Boxscore (`mlb.game_boxscore`)

`mlb.game_boxscore(game_pk: int, force_update: bool = False, context: BaseballContext | None = None) -> pl.DataFrame`

查詢單場比賽的球員 boxscore rows。

```python
import asyncio
import polars_baseball as pb

async def main() -> None:
    df = await pb.mlb.game_boxscore(745585)
    print(df.select(["gamePk", "teamId", "personId", "fullName"]))

if __name__ == "__main__":
    asyncio.run(main())
```

## 6. 球隊資料 (`mlb.teams`)

`mlb.teams(season: int | None = None, league_id: int | None = None, sport_id: int = 1, force_update: bool = False, context: BaseballContext | None = None) -> pl.DataFrame`

查詢官方 MLB 球隊 metadata。

```python
import asyncio
import polars_baseball as pb

async def main() -> None:
    df = await pb.mlb.teams(season=2024)
    print(df.select(["id", "name", "abbreviation", "leagueId"]))

if __name__ == "__main__":
    asyncio.run(main())
```

## 7. 球隊統計 (`mlb.team_stats`)

`mlb.team_stats(team_id: int, season: int | None = None, group: str = "hitting", stats_type: str = "season", force_update: bool = False, context: BaseballContext | None = None) -> pl.DataFrame`

查詢球隊層級的打擊、投球或守備統計。

```python
import asyncio
import polars_baseball as pb

async def main() -> None:
    df = await pb.mlb.team_stats(121, season=2024, group="hitting")
    print(df.head())

if __name__ == "__main__":
    asyncio.run(main())
```

## 8. 排行榜 (`mlb.stat_leaders`)

`mlb.stat_leaders(season: int, categories: list[str], limit: int = 10, stat_group: str | None = None, force_update: bool = False, context: BaseballContext | None = None) -> pl.DataFrame`

查詢一或多個統計類別的 league leaders。

```python
import asyncio
import polars_baseball as pb

async def main() -> None:
    df = await pb.mlb.stat_leaders(2024, ["homeRuns"], stat_group="hitting")
    print(df.head())

if __name__ == "__main__":
    asyncio.run(main())
```

## 9. 季後賽賽程 (`mlb.postseason_schedule`)

`mlb.postseason_schedule(season: int, force_update: bool = False, context: BaseballContext | None = None) -> pl.DataFrame`

查詢指定球季的 postseason games。

目前 live 驗證對近期已完成球季都回傳空 DataFrame，因此這裡刻意不提供「保證非空」的可執行範例。

## 10. Boxscore Stats (`mlb.game_boxscore_stats`)

`mlb.game_boxscore_stats(game_pk: int, force_update: bool = False, context: BaseballContext | None = None) -> pl.DataFrame`

查詢單場比賽攤平後的打擊、投球與守備 boxscore stats。

```python
import asyncio
import polars_baseball as pb

async def main() -> None:
    df = await pb.mlb.game_boxscore_stats(745585)
    print(df.head())

if __name__ == "__main__":
    asyncio.run(main())
```

## 11. Play-by-Play (`mlb.game_play_by_play`)

`mlb.game_play_by_play(game_pk: int, win_probability: bool = False, force_update: bool = False, context: BaseballContext | None = None) -> pl.DataFrame`

查詢單場比賽的 play-level data。設定 `win_probability=True` 時會使用 win probability endpoint。

```python
import asyncio
import polars_baseball as pb

async def main() -> None:
    df = await pb.mlb.game_play_by_play(745585)
    print(df.head())

if __name__ == "__main__":
    asyncio.run(main())
```

## 12. Win Probability (`mlb.game_win_probability`)

`mlb.game_win_probability(game_pk: int, force_update: bool = False, context: BaseballContext | None = None) -> pl.DataFrame`

查詢單場比賽每個 play 的 win probability、WPA、leverage 與 drama index 欄位。

```python
import asyncio
import polars_baseball as pb

async def main() -> None:
    df = await pb.mlb.game_win_probability(745585)
    print(df.head())

if __name__ == "__main__":
    asyncio.run(main())
```

## 13. 選秀資料 (`mlb.draft`)

`mlb.draft(year: int, draft_round: int | None = None, team_id: int | None = None, force_update: bool = False, context: BaseballContext | None = None) -> pl.DataFrame`

查詢特定年份的業餘選秀詳細資料，支援指定輪次與球隊篩選。

```python
import asyncio
import polars_baseball as pb

async def main() -> None:
    df = await pb.mlb.draft(year=2024)
    print(df.head())

if __name__ == "__main__":
    asyncio.run(main())
```

## 14. 球員球種庫 (`mlb.pitch_arsenal`)

`mlb.pitch_arsenal(person_id: int, season: int, force_update: bool = False, context: BaseballContext | None = None) -> pl.DataFrame`

查詢特定球員在該球季的球種庫數據（包含球種編碼、使用比例、平均球速等）。

```python
import asyncio
import polars_baseball as pb

async def main() -> None:
    df = await pb.mlb.pitch_arsenal(person_id=545361, season=2024)
    print(df.head())

if __name__ == "__main__":
    asyncio.run(main())
```

## 15. 交易記錄 (`mlb.transactions`)

`mlb.transactions(date: str | None = None, start_date: str | None = None, end_date: str | None = None, force_update: bool = False, context: BaseballContext | None = None) -> pl.DataFrame`

查詢指定日期或日期區間的球員異動與交易記錄。

```python
import asyncio
import polars_baseball as pb

async def main() -> None:
    df = await pb.mlb.transactions(date="2024-05-01")
    print(df.head())

if __name__ == "__main__":
    asyncio.run(main())
```

## 16. 球場與場館 (`mlb.venues`)

`mlb.venues(venue_ids: int | list[int] | None = None, force_update: bool = False, context: BaseballContext | None = None) -> pl.DataFrame`

查詢球場與場館的詳細元數據。

```python
import asyncio
import polars_baseball as pb

async def main() -> None:
    df = await pb.mlb.venues(venue_ids=[10, 20])
    print(df.head())

if __name__ == "__main__":
    asyncio.run(main())
```

## 17. 即時比賽資料流 (`mlb.game_feed_live`)

`mlb.game_feed_live(game_pk: int, force_update: bool = False, context: BaseballContext | None = None) -> pl.DataFrame`

呼叫 v1.1 live feed 端點獲取單場比賽極度細緻的即時事件與 Statcast 投球量測資料。

```python
import asyncio
import polars_baseball as pb

async def main() -> None:
    df = await pb.mlb.game_feed_live(game_pk=745585)
    print(df.head())

if __name__ == "__main__":
    asyncio.run(main())
```

## 18. 即時比分與局數數據 (`mlb.game_linescore`)

`mlb.game_linescore(game_pk: int, force_update: bool = False, cache_max_age: timedelta | None = timedelta(seconds=10), context: BaseballContext | None = None) -> pl.DataFrame`

獲取單場比賽每局的得分、安打與失誤數據。
可用 `cache_max_age` 依輪詢或已完賽查詢需求調整快取新鮮度；`force_update=True` 會略過快取。

```python
import asyncio
import polars_baseball as pb

async def main() -> None:
    df = await pb.mlb.game_linescore(game_pk=745585)
    print(df.head())

if __name__ == "__main__":
    asyncio.run(main())
```

## 19. 分區維度表 (`mlb.divisions`)

`mlb.divisions(sport_id: int = 1, force_update: bool = False, context: BaseballContext | None = None) -> pl.DataFrame`

獲取官方分區維度資料。

```python
import asyncio
import polars_baseball as pb

async def main() -> None:
    df = await pb.mlb.divisions()
    print(df.select(["id", "name", "leagueId", "active"]))

if __name__ == "__main__":
    asyncio.run(main())
```

## 20. 聯盟維度表 (`mlb.leagues`)

`mlb.leagues(sport_id: int = 1, force_update: bool = False, context: BaseballContext | None = None) -> pl.DataFrame`

獲取官方聯盟維度資料。

```python
import asyncio
import polars_baseball as pb

async def main() -> None:
    df = await pb.mlb.leagues()
    print(df.select(["id", "name", "abbreviation", "active"]))

if __name__ == "__main__":
    asyncio.run(main())
```

## 21. 個人獎項 (`mlb.people_awards`)

`mlb.people_awards(person_id: int, force_update: bool = False, context: BaseballContext | None = None) -> pl.DataFrame`

獲取官方單一人物獎項時間線資料。這不是 Lahman 獎項表或投票占比表的替代品。

```python
import asyncio
import polars_baseball as pb

async def main() -> None:
    df = await pb.mlb.people_awards(person_id=660271)
    print(df.select(["personId", "awardId", "awardName", "season"]))

if __name__ == "__main__":
    asyncio.run(main())
```

## 22. 戰績表 (`standings`)

`standings(season: int | None = None) -> pl.DataFrame`

獲取指定球季的 MLB 戰績表，其中包含分區（division）元數據欄位。

### 參數

- `season`：球季年份。如果省略，預設會查詢目前的球季。

```python
import asyncio
from polars_baseball import standings

async def main() -> None:
    df = await standings(2019)
    print(df.head())

if __name__ == "__main__":
    asyncio.run(main())
```
