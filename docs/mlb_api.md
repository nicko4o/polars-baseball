> [!NOTE]
> All public data-fetching APIs are asynchronous. Use `await` inside an async environment, or wrap calls with `asyncio.run()` in scripts.

# MLB Stats API

Provides access to official MLB Stats API endpoints (`statsapi.mlb.com`) for player bios, schedules, teams, rosters, game data, and leaderboards.

## 1. Player Bios (`mlb_people`)

`mlb_people(person_ids: list[int] | int, force_update: bool = False, context: BaseballContext | None = None) -> pl.DataFrame`

Retrieves biographical information for one or more players.

```python
import asyncio
from polars_baseball import mlb_people

async def main() -> None:
    df = await mlb_people(450314)
    print(df.select(["id", "fullName", "currentAge", "mlbDebutDate"]))

if __name__ == "__main__":
    asyncio.run(main())
```

## 2. Roster (`mlb_roster`)

`mlb_roster(team_id: int, season: int | None = None, roster_type: str = "active", force_update: bool = False, context: BaseballContext | None = None) -> pl.DataFrame`

Retrieves the roster for a team-season.

```python
import asyncio
from polars_baseball import mlb_roster

async def main() -> None:
    df = await mlb_roster(121, season=2024)
    print(df.select(["personId", "fullName", "jerseyNumber", "positionName"]))

if __name__ == "__main__":
    asyncio.run(main())
```

## 3. Schedule (`mlb_schedule`)

`mlb_schedule(season: int | None = None, date: str | None = None, team_id: int | None = None, hydrate: str | None = None, force_update: bool = False, context: BaseballContext | None = None) -> pl.DataFrame`

Retrieves MLB game schedules filtered by season, date, or team.

```python
import asyncio
from polars_baseball import mlb_schedule

async def main() -> None:
    df = await mlb_schedule(date="2024-05-06")
    print(df.select(["gamePk", "gameDate", "awayTeamName", "homeTeamName"]))

if __name__ == "__main__":
    asyncio.run(main())
```

## 4. Player Stats (`mlb_player_stats`)

`mlb_player_stats(person_id: int, group: str, stats_type: str = "season", season: int | None = None, force_update: bool = False, context: BaseballContext | None = None) -> pl.DataFrame`

Retrieves hitting, pitching, or fielding statistics for a player.

```python
import asyncio
from polars_baseball import mlb_player_stats

async def main() -> None:
    df = await mlb_player_stats(660271, group="hitting", stats_type="gameLog", season=2024)
    print(df.select(["season", "group", "statType", "gamesPlayed", "homeRuns"]))

if __name__ == "__main__":
    asyncio.run(main())
```

## 5. Game Boxscore (`mlb_game_boxscore`)

`mlb_game_boxscore(game_pk: int, force_update: bool = False, context: BaseballContext | None = None) -> pl.DataFrame`

Retrieves player boxscore rows for a single game.

```python
import asyncio
from polars_baseball import mlb_game_boxscore

async def main() -> None:
    df = await mlb_game_boxscore(715789)
    print(df.select(["gamePk", "teamId", "personId", "fullName"]))

if __name__ == "__main__":
    asyncio.run(main())
```

## 6. Teams (`mlb_teams`)

`mlb_teams(season: int | None = None, league_id: int | None = None, sport_id: int = 1, force_update: bool = False, context: BaseballContext | None = None) -> pl.DataFrame`

Retrieves official MLB team metadata.

```python
import asyncio
from polars_baseball import mlb_teams

async def main() -> None:
    df = await mlb_teams(season=2024)
    print(df.select(["id", "name", "abbreviation", "leagueId"]))

if __name__ == "__main__":
    asyncio.run(main())
```

## 7. Team Stats (`mlb_team_stats`)

`mlb_team_stats(team_id: int, season: int | None = None, group: str = "hitting", stats_type: str = "season", force_update: bool = False, context: BaseballContext | None = None) -> pl.DataFrame`

Retrieves team-level hitting, pitching, or fielding statistics.

```python
import asyncio
from polars_baseball import mlb_team_stats

async def main() -> None:
    df = await mlb_team_stats(121, season=2024, group="hitting")
    print(df.head())

if __name__ == "__main__":
    asyncio.run(main())
```

## 8. Stat Leaders (`mlb_stat_leaders`)

`mlb_stat_leaders(season: int, categories: list[str], limit: int = 10, stat_group: str | None = None, force_update: bool = False, context: BaseballContext | None = None) -> pl.DataFrame`

Retrieves league leaders for one or more stat categories.

```python
import asyncio
from polars_baseball import mlb_stat_leaders

async def main() -> None:
    df = await mlb_stat_leaders(2024, ["homeRuns"], stat_group="hitting")
    print(df.head())

if __name__ == "__main__":
    asyncio.run(main())
```

## 9. Postseason Schedule (`mlb_postseason_schedule`)

`mlb_postseason_schedule(season: int, force_update: bool = False, context: BaseballContext | None = None) -> pl.DataFrame`

Retrieves postseason games for a season.

```python
import asyncio
from polars_baseball import mlb_postseason_schedule

async def main() -> None:
    df = await mlb_postseason_schedule(2024)
    print(df.select(["gamePk", "gameDate", "awayTeamName", "homeTeamName"]))

if __name__ == "__main__":
    asyncio.run(main())
```

## 10. Game Boxscore Stats (`mlb_game_boxscore_stats`)

`mlb_game_boxscore_stats(game_pk: int, force_update: bool = False, context: BaseballContext | None = None) -> pl.DataFrame`

Retrieves flattened batting, pitching, and fielding stats from a single game boxscore.

```python
import asyncio
from polars_baseball import mlb_game_boxscore_stats

async def main() -> None:
    df = await mlb_game_boxscore_stats(715789)
    print(df.head())

if __name__ == "__main__":
    asyncio.run(main())
```

## 11. Play-by-Play (`mlb_game_play_by_play`)

`mlb_game_play_by_play(game_pk: int, win_probability: bool = False, force_update: bool = False, context: BaseballContext | None = None) -> pl.DataFrame`

Retrieves play-level data for a single game. Set `win_probability=True` to use the win probability endpoint.

```python
import asyncio
from polars_baseball import mlb_game_play_by_play

async def main() -> None:
    df = await mlb_game_play_by_play(715789)
    print(df.head())

if __name__ == "__main__":
    asyncio.run(main())
```

## 12. Win Probability (`mlb_game_win_probability`)

`mlb_game_win_probability(game_pk: int, force_update: bool = False, context: BaseballContext | None = None) -> pl.DataFrame`

Retrieves per-play win probability, WPA, leverage, and drama index fields for a single game.

```python
import asyncio
from polars_baseball import mlb_game_win_probability

async def main() -> None:
    df = await mlb_game_win_probability(715789)
    print(df.head())

if __name__ == "__main__":
    asyncio.run(main())
```

## 13. Draft (`mlb_draft`)

`mlb_draft(year: int, draft_round: int | None = None, team_id: int | None = None, force_update: bool = False, context: BaseballContext | None = None) -> pl.DataFrame`

Retrieves amateur draft details for a specific year, with optional round and team filtering.

```python
import asyncio
from polars_baseball import mlb_draft

async def main() -> None:
    df = await mlb_draft(year=2024)
    print(df.head())

if __name__ == "__main__":
    asyncio.run(main())
```

## 14. Pitch Arsenal (`mlb_pitch_arsenal`)

`mlb_pitch_arsenal(person_id: int, season: int, force_update: bool = False, context: BaseballContext | None = None) -> pl.DataFrame`

Retrieves a player's pitch arsenal stats (average speed, percentage, etc.) for a season.

```python
import asyncio
from polars_baseball import mlb_pitch_arsenal

async def main() -> None:
    df = await mlb_pitch_arsenal(person_id=545361, season=2024)
    print(df.head())

if __name__ == "__main__":
    asyncio.run(main())
```

## 15. Transactions (`mlb_transactions`)

`mlb_transactions(date: str | None = None, start_date: str | None = None, end_date: str | None = None, force_update: bool = False, context: BaseballContext | None = None) -> pl.DataFrame`

Retrieves transaction records for a specific date or date range.

```python
import asyncio
from polars_baseball import mlb_transactions

async def main() -> None:
    df = await mlb_transactions(date="2024-05-01")
    print(df.head())

if __name__ == "__main__":
    asyncio.run(main())
```

## 16. Venues (`mlb_venues`)

`mlb_venues(venue_ids: int | list[int] | None = None, force_update: bool = False, context: BaseballContext | None = None) -> pl.DataFrame`

Retrieves stadium and venue metadata.

```python
import asyncio
from polars_baseball import mlb_venues

async def main() -> None:
    df = await mlb_venues(venue_ids=[10, 20])
    print(df.head())

if __name__ == "__main__":
    asyncio.run(main())
```

## 17. Game Feed Live (`mlb_game_feed_live`)

`mlb_game_feed_live(game_pk: int, force_update: bool = False, context: BaseballContext | None = None) -> pl.DataFrame`

Retrieves granular, real-time live feed events and pitch Statcast measurements for a game.

```python
import asyncio
from polars_baseball import mlb_game_feed_live

async def main() -> None:
    df = await mlb_game_feed_live(game_pk=715789)
    print(df.head())

if __name__ == "__main__":
    asyncio.run(main())
```

## 18. Game Linescore (`mlb_game_linescore`)

`mlb_game_linescore(game_pk: int, force_update: bool = False, cache_max_age: timedelta | None = timedelta(seconds=10), context: BaseballContext | None = None) -> pl.DataFrame`

Retrieves inning-by-inning linescore data (runs, hits, errors) for a game.
Use `cache_max_age` to tune freshness for polling or completed games; `force_update=True` bypasses the cache.

```python
import asyncio
from polars_baseball import mlb_game_linescore

async def main() -> None:
    df = await mlb_game_linescore(game_pk=715789)
    print(df.head())

if __name__ == "__main__":
    asyncio.run(main())
```

## 19. Divisions (`mlb_divisions`)

`mlb_divisions(sport_id: int = 1, force_update: bool = False, context: BaseballContext | None = None) -> pl.DataFrame`

Retrieves official division dimension metadata.

```python
import asyncio
from polars_baseball import mlb_divisions

async def main() -> None:
    df = await mlb_divisions()
    print(df.select(["id", "name", "leagueId", "active"]))

if __name__ == "__main__":
    asyncio.run(main())
```

## 20. Leagues (`mlb_leagues`)

`mlb_leagues(sport_id: int = 1, force_update: bool = False, context: BaseballContext | None = None) -> pl.DataFrame`

Retrieves official league dimension metadata.

```python
import asyncio
from polars_baseball import mlb_leagues

async def main() -> None:
    df = await mlb_leagues()
    print(df.select(["id", "name", "abbreviation", "active"]))

if __name__ == "__main__":
    asyncio.run(main())
```

## 21. People Awards (`mlb_people_awards`)

`mlb_people_awards(person_id: int, force_update: bool = False, context: BaseballContext | None = None) -> pl.DataFrame`

Retrieves official person-centric MLB award timeline rows. This does not replace Lahman award or award vote-share tables.

```python
import asyncio
from polars_baseball import mlb_people_awards

async def main() -> None:
    df = await mlb_people_awards(person_id=660271)
    print(df.select(["personId", "awardId", "awardName", "season"]))

if __name__ == "__main__":
    asyncio.run(main())
```
