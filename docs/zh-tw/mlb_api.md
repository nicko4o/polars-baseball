> [!NOTE]
> 所有公開資料擷取 API 都是非同步函式。請在 async 環境中使用 `await`，或在指令碼中用 `asyncio.run()` 包裝呼叫。

# MLB Stats API

提供官方 MLB Stats API 端點 (`statsapi.mlb.com`) 的存取，用以查詢球員、賽程、球隊、名冊、比賽資料與排行榜。

## 1. 球員基本資料 (`mlb_people`)

`mlb_people(person_ids: list[int] | int, force_update: bool = False, context: BaseballContext | None = None) -> pl.DataFrame`

查詢一或多位球員的基本資料。

```python
import asyncio
from polars_baseball import mlb_people

async def main() -> None:
    df = await mlb_people(450314)
    print(df.select(["id", "fullName", "currentAge", "mlbDebutDate"]))

if __name__ == "__main__":
    asyncio.run(main())
```

## 2. 球隊名冊 (`mlb_roster`)

`mlb_roster(team_id: int, season: int | None = None, roster_type: str = "active", force_update: bool = False, context: BaseballContext | None = None) -> pl.DataFrame`

查詢指定球隊與球季的名冊。

```python
import asyncio
from polars_baseball import mlb_roster

async def main() -> None:
    df = await mlb_roster(121, season=2024)
    print(df.select(["personId", "fullName", "jerseyNumber", "positionName"]))

if __name__ == "__main__":
    asyncio.run(main())
```

## 3. 賽程 (`mlb_schedule`)

`mlb_schedule(season: int | None = None, date: str | None = None, team_id: int | None = None, hydrate: str | None = None, force_update: bool = False, context: BaseballContext | None = None) -> pl.DataFrame`

依球季、日期或球隊查詢 MLB 賽程。

```python
import asyncio
from polars_baseball import mlb_schedule

async def main() -> None:
    df = await mlb_schedule(date="2024-05-06")
    print(df.select(["gamePk", "gameDate", "awayTeamName", "homeTeamName"]))

if __name__ == "__main__":
    asyncio.run(main())
```

## 4. 球員統計 (`mlb_player_stats`)

`mlb_player_stats(person_id: int, group: str, stats_type: str = "season", season: int | None = None, force_update: bool = False, context: BaseballContext | None = None) -> pl.DataFrame`

查詢球員打擊、投球或守備統計。

```python
import asyncio
from polars_baseball import mlb_player_stats

async def main() -> None:
    df = await mlb_player_stats(660271, group="hitting", stats_type="gameLog", season=2024)
    print(df.select(["season", "group", "statType", "gamesPlayed", "homeRuns"]))

if __name__ == "__main__":
    asyncio.run(main())
```

## 5. Boxscore (`mlb_game_boxscore`)

`mlb_game_boxscore(game_pk: int, force_update: bool = False, context: BaseballContext | None = None) -> pl.DataFrame`

查詢單場比賽的球員 boxscore rows。

```python
import asyncio
from polars_baseball import mlb_game_boxscore

async def main() -> None:
    df = await mlb_game_boxscore(745585)
    print(df.select(["gamePk", "teamId", "personId", "fullName"]))

if __name__ == "__main__":
    asyncio.run(main())
```

## 6. 球隊資料 (`mlb_teams`)

`mlb_teams(season: int | None = None, league_id: int | None = None, sport_id: int = 1, force_update: bool = False, context: BaseballContext | None = None) -> pl.DataFrame`

查詢官方 MLB 球隊 metadata。

```python
import asyncio
from polars_baseball import mlb_teams

async def main() -> None:
    df = await mlb_teams(season=2024)
    print(df.select(["id", "name", "abbreviation", "leagueId"]))

if __name__ == "__main__":
    asyncio.run(main())
```

## 7. 球隊統計 (`mlb_team_stats`)

`mlb_team_stats(team_id: int, season: int | None = None, group: str = "hitting", stats_type: str = "season", force_update: bool = False, context: BaseballContext | None = None) -> pl.DataFrame`

查詢球隊層級的打擊、投球或守備統計。

```python
import asyncio
from polars_baseball import mlb_team_stats

async def main() -> None:
    df = await mlb_team_stats(121, season=2024, group="hitting")
    print(df.head())

if __name__ == "__main__":
    asyncio.run(main())
```

## 8. 排行榜 (`mlb_stat_leaders`)

`mlb_stat_leaders(season: int, categories: list[str], limit: int = 10, stat_group: str | None = None, force_update: bool = False, context: BaseballContext | None = None) -> pl.DataFrame`

查詢一或多個統計類別的 league leaders。

```python
import asyncio
from polars_baseball import mlb_stat_leaders

async def main() -> None:
    df = await mlb_stat_leaders(2024, ["homeRuns"], stat_group="hitting")
    print(df.head())

if __name__ == "__main__":
    asyncio.run(main())
```

## 9. 季後賽賽程 (`mlb_postseason_schedule`)

`mlb_postseason_schedule(season: int, force_update: bool = False, context: BaseballContext | None = None) -> pl.DataFrame`

查詢指定球季的 postseason games。

目前 live 驗證對近期已完成球季都回傳空 DataFrame，因此這裡刻意不提供「保證非空」的可執行範例。

## 10. Boxscore Stats (`mlb_game_boxscore_stats`)

`mlb_game_boxscore_stats(game_pk: int, force_update: bool = False, context: BaseballContext | None = None) -> pl.DataFrame`

查詢單場比賽攤平後的打擊、投球與守備 boxscore stats。

```python
import asyncio
from polars_baseball import mlb_game_boxscore_stats

async def main() -> None:
    df = await mlb_game_boxscore_stats(745585)
    print(df.head())

if __name__ == "__main__":
    asyncio.run(main())
```

## 11. Play-by-Play (`mlb_game_play_by_play`)

`mlb_game_play_by_play(game_pk: int, win_probability: bool = False, force_update: bool = False, context: BaseballContext | None = None) -> pl.DataFrame`

查詢單場比賽的 play-level data。設定 `win_probability=True` 時會使用 win probability endpoint。

```python
import asyncio
from polars_baseball import mlb_game_play_by_play

async def main() -> None:
    df = await mlb_game_play_by_play(745585)
    print(df.head())

if __name__ == "__main__":
    asyncio.run(main())
```

## 12. Win Probability (`mlb_game_win_probability`)

`mlb_game_win_probability(game_pk: int, force_update: bool = False, context: BaseballContext | None = None) -> pl.DataFrame`

查詢單場比賽每個 play 的 win probability、WPA、leverage 與 drama index 欄位。

```python
import asyncio
from polars_baseball import mlb_game_win_probability

async def main() -> None:
    df = await mlb_game_win_probability(745585)
    print(df.head())

if __name__ == "__main__":
    asyncio.run(main())
```

## 13. 選秀資料 (`mlb_draft`)

`mlb_draft(year: int, draft_round: int | None = None, team_id: int | None = None, force_update: bool = False, context: BaseballContext | None = None) -> pl.DataFrame`

查詢特定年份的業餘選秀詳細資料，支援指定輪次與球隊篩選。

```python
import asyncio
from polars_baseball import mlb_draft

async def main() -> None:
    df = await mlb_draft(year=2024)
    print(df.head())

if __name__ == "__main__":
    asyncio.run(main())
```

## 14. 球員球種庫 (`mlb_pitch_arsenal`)

`mlb_pitch_arsenal(person_id: int, season: int, force_update: bool = False, context: BaseballContext | None = None) -> pl.DataFrame`

查詢特定球員在該球季的球種庫數據（包含球種編碼、使用比例、平均球速等）。

```python
import asyncio
from polars_baseball import mlb_pitch_arsenal

async def main() -> None:
    df = await mlb_pitch_arsenal(person_id=545361, season=2024)
    print(df.head())

if __name__ == "__main__":
    asyncio.run(main())
```

## 15. 交易記錄 (`mlb_transactions`)

`mlb_transactions(date: str | None = None, start_date: str | None = None, end_date: str | None = None, force_update: bool = False, context: BaseballContext | None = None) -> pl.DataFrame`

查詢指定日期或日期區間的球員異動與交易記錄。

```python
import asyncio
from polars_baseball import mlb_transactions

async def main() -> None:
    df = await mlb_transactions(date="2024-05-01")
    print(df.head())

if __name__ == "__main__":
    asyncio.run(main())
```

## 16. 球場與場館 (`mlb_venues`)

`mlb_venues(venue_ids: int | list[int] | None = None, force_update: bool = False, context: BaseballContext | None = None) -> pl.DataFrame`

查詢球場與場館的詳細元數據。

```python
import asyncio
from polars_baseball import mlb_venues

async def main() -> None:
    df = await mlb_venues(venue_ids=[10, 20])
    print(df.head())

if __name__ == "__main__":
    asyncio.run(main())
```

## 17. 即時比賽資料流 (`mlb_game_feed_live`)

`mlb_game_feed_live(game_pk: int, force_update: bool = False, context: BaseballContext | None = None) -> pl.DataFrame`

呼叫 v1.1 live feed 端點獲取單場比賽極度細緻的即時事件與 Statcast 投球量測資料。

```python
import asyncio
from polars_baseball import mlb_game_feed_live

async def main() -> None:
    df = await mlb_game_feed_live(game_pk=745585)
    print(df.head())

if __name__ == "__main__":
    asyncio.run(main())
```

## 18. 即時比分與局數數據 (`mlb_game_linescore`)

`mlb_game_linescore(game_pk: int, force_update: bool = False, cache_max_age: timedelta | None = timedelta(seconds=10), context: BaseballContext | None = None) -> pl.DataFrame`

獲取單場比賽每局的得分、安打與失誤數據。
可用 `cache_max_age` 依輪詢或已完賽查詢需求調整快取新鮮度；`force_update=True` 會略過快取。

```python
import asyncio
from polars_baseball import mlb_game_linescore

async def main() -> None:
    df = await mlb_game_linescore(game_pk=745585)
    print(df.head())

if __name__ == "__main__":
    asyncio.run(main())
```

## 19. 分區維度表 (`mlb_divisions`)

`mlb_divisions(sport_id: int = 1, force_update: bool = False, context: BaseballContext | None = None) -> pl.DataFrame`

獲取官方分區維度資料。

```python
import asyncio
from polars_baseball import mlb_divisions

async def main() -> None:
    df = await mlb_divisions()
    print(df.select(["id", "name", "leagueId", "active"]))

if __name__ == "__main__":
    asyncio.run(main())
```

## 20. 聯盟維度表 (`mlb_leagues`)

`mlb_leagues(sport_id: int = 1, force_update: bool = False, context: BaseballContext | None = None) -> pl.DataFrame`

獲取官方聯盟維度資料。

```python
import asyncio
from polars_baseball import mlb_leagues

async def main() -> None:
    df = await mlb_leagues()
    print(df.select(["id", "name", "abbreviation", "active"]))

if __name__ == "__main__":
    asyncio.run(main())
```

## 21. 球員獎項時間線 (`mlb_people_awards`)

`mlb_people_awards(person_id: int, force_update: bool = False, context: BaseballContext | None = None) -> pl.DataFrame`

獲取官方單一人物獎項時間線資料。這不是 Lahman 獎項表或投票占比表的替代品。

```python
import asyncio
from polars_baseball import mlb_people_awards

async def main() -> None:
    df = await mlb_people_awards(person_id=660271)
    print(df.select(["personId", "awardId", "awardName", "season"]))

if __name__ == "__main__":
    asyncio.run(main())
```
