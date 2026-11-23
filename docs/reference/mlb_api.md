> [!NOTE]
> All public data-fetching APIs are asynchronous. Use `await` inside an async environment, or `asyncio.run()` in scripts.

# MLB Stats API

Access official MLB Stats API endpoints (`statsapi.mlb.com`) and MLB Film Room video search via `client.mlb`.

> [!TIP]
> Player endpoints require numeric MLBAM `person_id` values. Use `await client.lookup.playerid_lookup("Ohtani", "Shohei")` to find `key_mlbam`.

All endpoints enforce strict Polars schemas defined in [`polars_baseball/_schemas/mlb.py`](https://github.com/nicko4o/polars-baseball/blob/main/polars_baseball/_schemas/mlb.py).

## Example

```python
import asyncio
import polars_baseball as pb


async def main() -> None:
    async with pb.BaseballClient() as client:
        schedule = await client.mlb.schedule(date="2026-06-01")
        leaders = await client.mlb.stat_leaders(["homeRuns"], season=2026, stat_group="hitting")
        print(schedule.select(["gamePk", "awayTeamName", "homeTeamName"]).head())
        print(leaders.head())


if __name__ == "__main__":
    asyncio.run(main())
```

## Available Methods

`divisions`, `draft`, `film_room_search`, `game_boxscore`, `game_boxscore_stats`, `game_feed_live`, `game_highlights`, `game_linescore`, `game_play_by_play`, `game_win_probability`, `leagues`, `people`, `people_awards`, `pitch_arsenal`, `player_stats`, `postseason_schedule`, `prospect_rankings`, `resolve_team_id`, `roster`, `schedule`, `standings`, `stat_leaders`, `team_stats`, `teams`, `top_prospects`, `transactions`, `venues`.

## API Reference

::: polars_baseball.mlb.MlbClient
