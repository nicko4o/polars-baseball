> [!NOTE]
> All public data-fetching APIs are asynchronous. Use `await` inside an async environment, or wrap calls with `asyncio.run()` in scripts.

# MLB Stats API

Use this when: you need official MLB endpoint data such as schedules, rosters, game feeds, boxscores, transactions, or metadata.
Do not use this when: you need FanGraphs leaderboards, Lahman historical tables, or Baseball Savant pitch-level search.
Output grain: endpoint-specific rows such as games, people, roster entries, plays, innings, or dimension records.
Source: MLB Stats API.

Provides access to official MLB Stats API endpoints (`statsapi.mlb.com`) for player bios, schedules, teams, rosters, game data, and leaderboards.
New code can call the shorter `polars_baseball.mlb` namespace, such as `pb.mlb.schedule(...)`.

## API Groups

| Group | APIs | Use when |
| --- | --- | --- |
| Identity | `mlb.people`, `mlb.people_awards` | You need official person metadata or award timelines. |
| Schedule and team metadata | `mlb.schedule`, `mlb.teams`, `mlb.roster`, `mlb.venues`, `mlb.divisions`, `mlb.leagues` | You need game lists, roster snapshots, or joinable dimension tables. |
| Game data | `mlb.game_boxscore`, `mlb.game_boxscore_stats`, `mlb.game_play_by_play`, `mlb.game_win_probability`, `mlb.game_feed_live`, `mlb.game_linescore` | You need single-game player, play, live-feed, or inning data. |
| Stats and leaderboards | `mlb.player_stats`, `mlb.team_stats`, `mlb.stat_leaders`, `mlb.pitch_arsenal`, `standings` | You need official stat groups, league leaders, or standings. |
| Operations | `mlb.transactions`, `mlb.draft`, `mlb.postseason_schedule` | You need roster movement, draft records, or postseason schedule rows. |

> [!TIP]
> Functions below require numeric `person_id` or `person_ids` (MLBAM ID).
> Don't know the ID? Use `pb.playerid_lookup("Ohtani", "Shohei")` or `pb.player_name_suggestions("oht")` to find the `key_mlbam`.

## 1. Player Bios (`mlb.people`)

`mlb.people(person_ids: list[int] | int, force_update: bool = False, context: BaseballContext | None = None) -> pl.DataFrame`

Retrieves biographical information for one or more players.

```python
import asyncio

import polars_baseball as pb

async def main() -> None:
    df = await pb.mlb.people(450314)
    print(df.select(["id", "fullName", "currentAge", "mlbDebutDate"]))

if __name__ == "__main__":
    asyncio.run(main())
```

## 2. Roster (`mlb.roster`)

`mlb.roster(team_id: int, season: int | None = None, roster_type: str = "active", force_update: bool = False, context: BaseballContext | None = None) -> pl.DataFrame`

Retrieves the roster for a team-season.

```python
import asyncio

import polars_baseball as pb

async def main() -> None:
    df = await pb.mlb.roster(121, season=2026)
    print(df.select(["personId", "fullName", "jerseyNumber", "positionName"]))

if __name__ == "__main__":
    asyncio.run(main())
```

## 3. Schedule (`mlb.schedule`)

`mlb.schedule(season: int | None = None, date: str | None = None, team_id: int | None = None, hydrate: str | None = None, force_update: bool = False, context: BaseballContext | None = None) -> pl.DataFrame`

Retrieves MLB game schedules filtered by season, date, or team.

```python
import asyncio

import polars_baseball as pb

async def main() -> None:
    df = await pb.mlb.schedule(date="2026-06-01")
    print(df.select(["gamePk", "gameDate", "awayTeamName", "homeTeamName"]))

if __name__ == "__main__":
    asyncio.run(main())
```

## 4. Player Stats (`mlb.player_stats`)

`mlb.player_stats(person_id: int, group: str, stats_type: str = "season", season: int | None = None, force_update: bool = False, context: BaseballContext | None = None) -> pl.DataFrame`

Retrieves hitting, pitching, or fielding statistics for a player.

```python
import asyncio
import polars_baseball as pb

async def main() -> None:
    df = await pb.mlb.player_stats(660271, group="hitting", stats_type="gameLog", season=2026)
    print(df.select(["season", "group", "statType", "gamesPlayed", "homeRuns"]))

if __name__ == "__main__":
    asyncio.run(main())
```

## 5. Game Boxscore (`mlb.game_boxscore`)

`mlb.game_boxscore(game_pk: int, force_update: bool = False, context: BaseballContext | None = None) -> pl.DataFrame`

Retrieves player boxscore rows for a single game.

```python
import asyncio
import polars_baseball as pb

async def main() -> None:
    df = await pb.mlb.game_boxscore(745585)
    print(df.select(["gamePk", "teamId", "personId", "fullName"]))

if __name__ == "__main__":
    asyncio.run(main())
```

## 6. Teams (`mlb.teams`)

`mlb.teams(season: int | None = None, league_id: int | None = None, sport_id: int = 1, force_update: bool = False, context: BaseballContext | None = None) -> pl.DataFrame`

Retrieves official MLB team metadata.

```python
import asyncio
import polars_baseball as pb

async def main() -> None:
    df = await pb.mlb.teams(season=2026)
    print(df.select(["id", "name", "abbreviation", "leagueId"]))

if __name__ == "__main__":
    asyncio.run(main())
```

## 7. Team Stats (`mlb.team_stats`)

`mlb.team_stats(team_id: int, season: int | None = None, group: str = "hitting", stats_type: str = "season", force_update: bool = False, context: BaseballContext | None = None) -> pl.DataFrame`

Retrieves team-level hitting, pitching, or fielding statistics.

```python
import asyncio
import polars_baseball as pb

async def main() -> None:
    df = await pb.mlb.team_stats(121, season=2026, group="hitting")
    print(df.head())

if __name__ == "__main__":
    asyncio.run(main())
```

## 8. Stat Leaders (`mlb.stat_leaders`)

`mlb.stat_leaders(season: int, categories: list[str], limit: int = 10, stat_group: str | None = None, force_update: bool = False, context: BaseballContext | None = None) -> pl.DataFrame`

Retrieves league leaders for one or more stat categories.

```python
import asyncio
import polars_baseball as pb

async def main() -> None:
    df = await pb.mlb.stat_leaders(2026, ["homeRuns"], stat_group="hitting")
    print(df.head())

if __name__ == "__main__":
    asyncio.run(main())
```

## 9. Postseason Schedule (`mlb.postseason_schedule`)

`mlb.postseason_schedule(season: int, force_update: bool = False, context: BaseballContext | None = None) -> pl.DataFrame`

Retrieves postseason games for a season.

Current live checks return an empty DataFrame for recent completed seasons, so this reference intentionally does not provide a guaranteed non-empty example.

## 10. Game Boxscore Stats (`mlb.game_boxscore_stats`)

`mlb.game_boxscore_stats(game_pk: int, force_update: bool = False, context: BaseballContext | None = None) -> pl.DataFrame`

Retrieves flattened batting, pitching, and fielding stats from a single game boxscore.

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

Retrieves play-level data for a single game. Set `win_probability=True` to use the win probability endpoint.

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

Retrieves per-play win probability, WPA, leverage, and drama index fields for a single game.

```python
import asyncio
import polars_baseball as pb

async def main() -> None:
    df = await pb.mlb.game_win_probability(745585)
    print(df.head())

if __name__ == "__main__":
    asyncio.run(main())
```

## 13. Draft (`mlb.draft`)

`mlb.draft(year: int, draft_round: int | None = None, team_id: int | None = None, force_update: bool = False, context: BaseballContext | None = None) -> pl.DataFrame`

Retrieves amateur draft details for a specific year, with optional round and team filtering.

```python
import asyncio
import polars_baseball as pb

async def main() -> None:
    df = await pb.mlb.draft(year=2026)
    print(df.head())

if __name__ == "__main__":
    asyncio.run(main())
```

## 14. Pitch Arsenal (`mlb.pitch_arsenal`)

`mlb.pitch_arsenal(person_id: int, season: int, force_update: bool = False, context: BaseballContext | None = None) -> pl.DataFrame`

Retrieves a player's pitch arsenal stats (average speed, percentage, etc.) for a season.

```python
import asyncio
import polars_baseball as pb

async def main() -> None:
    df = await pb.mlb.pitch_arsenal(person_id=545361, season=2026)
    print(df.head())

if __name__ == "__main__":
    asyncio.run(main())
```

## 15. Transactions (`mlb.transactions`)

`mlb.transactions(date: str | None = None, start_date: str | None = None, end_date: str | None = None, force_update: bool = False, context: BaseballContext | None = None) -> pl.DataFrame`

Retrieves transaction records for a specific date or date range.

```python
import asyncio
import polars_baseball as pb

async def main() -> None:
    df = await pb.mlb.transactions(date="2026-06-01")
    print(df.head())

if __name__ == "__main__":
    asyncio.run(main())
```

## 16. Venues (`mlb.venues`)

`mlb.venues(venue_ids: int | list[int] | None = None, force_update: bool = False, context: BaseballContext | None = None) -> pl.DataFrame`

Retrieves stadium and venue metadata.

```python
import asyncio
import polars_baseball as pb

async def main() -> None:
    df = await pb.mlb.venues(venue_ids=[10, 20])
    print(df.head())

if __name__ == "__main__":
    asyncio.run(main())
```

## 17. Game Feed Live (`mlb.game_feed_live`)

`mlb.game_feed_live(game_pk: int, force_update: bool = False, context: BaseballContext | None = None) -> pl.DataFrame`

Retrieves granular, real-time live feed events and pitch Statcast measurements for a game.

```python
import asyncio
import polars_baseball as pb

async def main() -> None:
    df = await pb.mlb.game_feed_live(game_pk=745585)
    print(df.head())

if __name__ == "__main__":
    asyncio.run(main())
```

## 18. Game Linescore (`mlb.game_linescore`)

`mlb.game_linescore(game_pk: int, force_update: bool = False, cache_max_age: timedelta | None = timedelta(seconds=10), context: BaseballContext | None = None) -> pl.DataFrame`

Retrieves inning-by-inning linescore data (runs, hits, errors) for a game.
Use `cache_max_age` to tune freshness for polling or completed games; `force_update=True` bypasses the cache.

```python
import asyncio
import polars_baseball as pb

async def main() -> None:
    df = await pb.mlb.game_linescore(game_pk=745585)
    print(df.head())

if __name__ == "__main__":
    asyncio.run(main())
```

## 19. Divisions (`mlb.divisions`)

`mlb.divisions(sport_id: int = 1, force_update: bool = False, context: BaseballContext | None = None) -> pl.DataFrame`

Retrieves official division dimension metadata.

```python
import asyncio
import polars_baseball as pb

async def main() -> None:
    df = await pb.mlb.divisions()
    print(df.select(["id", "name", "leagueId", "active"]))

if __name__ == "__main__":
    asyncio.run(main())
```

## 20. Leagues (`mlb.leagues`)

`mlb.leagues(sport_id: int = 1, force_update: bool = False, context: BaseballContext | None = None) -> pl.DataFrame`

Retrieves official league dimension metadata.

```python
import asyncio
import polars_baseball as pb

async def main() -> None:
    df = await pb.mlb.leagues()
    print(df.select(["id", "name", "abbreviation", "active"]))

if __name__ == "__main__":
    asyncio.run(main())
```

## 21. People Awards (`mlb.people_awards`)

`mlb.people_awards(person_id: int, force_update: bool = False, context: BaseballContext | None = None) -> pl.DataFrame`

Retrieves official person-centric MLB award timeline rows. This does not replace Lahman award or award vote-share tables.

```python
import asyncio
import polars_baseball as pb

async def main() -> None:
    df = await pb.mlb.people_awards(person_id=660271)
    print(df.select(["personId", "awardId", "awardName", "season"]))

if __name__ == "__main__":
    asyncio.run(main())
```

## 22. Standings (`standings`)

`standings(season: int | None = None) -> pl.DataFrame`

Retrieves one MLB standings table for a season, with division metadata columns.

### Arguments

- `season`: Season year. If omitted, the current season is requested.

```python
import asyncio
from polars_baseball import standings

async def main() -> None:
    df = await standings(2019)
    print(df.head())

if __name__ == "__main__":
    asyncio.run(main())
```

