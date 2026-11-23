> [!NOTE]
> All public data-fetching APIs are asynchronous (`async def`). Use `await` inside an async environment (including Jupyter/IPython cells—do not wrap notebook calls in `asyncio.run()`), or `asyncio.run()` in standalone scripts.
>
> Date parameters accept both `YYYY-MM-DD` strings and `datetime.date` objects.

# Documentation

## API Use-Case Index

| Use case | Recommended API | Source |
| --- | --- | --- |
| Pitch-level data (range, pitcher, batter, game) | `client.savant.statcast`, `pitcher`, `batter`, `single_game` | Baseball Savant |
| Statcast leaderboards & park factors | `client.savant.expected_stats`, `pitcher_pitch_arsenal`, `park_factors` | Baseball Savant |
| Local partitioned Statcast Parquet dataset | `client.savant.sync_statcast`, `scan_statcast` | Baseball Savant |
| FanGraphs player & team leaderboards | `client.fangraphs.batting`, `pitching`, `fielding`, `team_batting`, `season_schedule` | FanGraphs |
| MLB schedules, rosters, bios, standings | `client.mlb.schedule`, `roster`, `people`, `standings`, `teams` | MLB Stats API |
| MLB game boxscores, play-by-play, live feeds | `client.mlb.game_boxscore`, `game_play_by_play`, `game_win_probability`, `game_feed_live` | MLB Stats API |
| MLB stats, transactions, draft, Film Room, prospects | `client.mlb.player_stats`, `transactions`, `draft`, `film_room_search`, `top_prospects` | MLB Stats API |
| Lahman historical tables | `client.lahman.batting`, `pitching`, `people`, `teams_core` | Lahman |
| Retrosheet events, logs, rosters, schedules | `client.retrosheet.events`, `season_game_logs`, `rosters`, `schedules` | Retrosheet |
| Baseball Reference WAR, game logs, splits | `client.bref.bwar_bat`, `bwar_pitch`, `game_logs`, `splits` | Baseball Reference |
| Player & team ID lookups | `client.lookup.playerid_lookup`, `playerid_reverse_lookup`, `chadwick_register`, `team_ids` | Chadwick / Static |

## Guides

- [Caching & Storage](guides/caching.md)
- [Error Handling & Production Resilience](guides/error_handling.md)

## Provider Reference

- [Statcast / Savant](reference/statcast.md)
- [FanGraphs](reference/fangraphs.md)
- [MLB Stats API](reference/mlb_api.md)
- [Lookups & Mappings](reference/lookups.md)
- [Baseball Reference](reference/bref.md)
- [Lahman](reference/lahman.md)
- [Retrosheet](reference/retrosheet.md)
- [Stability & Upstream Schema Policy](reference/stability.md)

## Notebooks & Maintenance

- [`notebooks/statcast_pitch_mix_demo.ipynb`](https://github.com/nicko4o/polars-baseball/blob/main/notebooks/statcast_pitch_mix_demo.ipynb)
- [`notebooks/fangraphs_leaderboard_demo.ipynb`](https://github.com/nicko4o/polars-baseball/blob/main/notebooks/fangraphs_leaderboard_demo.ipynb)
- [`notebooks/mlb_schedule_demo.ipynb`](https://github.com/nicko4o/polars-baseball/blob/main/notebooks/mlb_schedule_demo.ipynb)
- [Documentation Maintenance Rules](MAINTAINING.md)
