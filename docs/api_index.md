> [!NOTE]
> All public data-fetching APIs are asynchronous. Use `await` inside an async environment, or wrap calls with `asyncio.run()` in scripts.
>
> Date parameters accept both `YYYY-MM-DD` strings and `datetime.date` objects.

# API Use-Case Index

Use this page to choose an API by task. Provider-specific pages still hold the detailed signatures, arguments, examples, and edge cases.

| Use case | Recommended API | Output grain | Source | Best for |
| --- | --- | --- | --- | --- |
| Query pitch-level data for a date range | `client.savant.statcast` | One row per pitch | Baseball Savant | Pitch mix, velocity, batted-ball, and plate appearance analysis |
| Query pitch-level data for one pitcher | `client.savant.pitcher` | One row per pitch | Baseball Savant | Pitcher arsenal, pitch mix, and opponent outcome analysis |
| Query pitch-level data for one batter | `client.savant.batter` | One row per pitch | Baseball Savant | Batter matchup, swing, contact, and batted-ball analysis |
| Query pitch-level data for one game | `client.savant.single_game` | One row per pitch | Baseball Savant | Single-game pitch breakdowns by `game_pk` |
| Query batter or pitcher leaderboards | `client.savant.expected_stats`, `client.savant.pitcher_pitch_arsenal`, and related helpers | Leaderboard rows | Baseball Savant | Season-level Statcast leaderboard metrics |
| Query venue Statcast Park Factors | `client.savant.park_factors` | Park factor rows | Baseball Savant | Stadium HR, wOBA, SO, BB, and hit metric park factors |
| Persist and lazily query full-season Statcast data locally | `client.savant.sync_statcast`, `client.savant.scan_statcast` | One row per pitch | Baseball Savant (local compiled Parquet dataset) | Big-data queries with predicate/projection pushdown over Hive-partitioned seasons |
| Query FanGraphs player leaderboards | `client.fangraphs.batting`, `client.fangraphs.pitching`, `client.fangraphs.fielding` | Leaderboard rows | FanGraphs | Player batting, pitching, and fielding leaderboards |
| Query FanGraphs team leaderboards & schedules | `client.fangraphs.team_batting`, `client.fangraphs.team_pitching`, `client.fangraphs.season_schedule`, and related helpers | Team leaderboard rows | FanGraphs | Team-level season comparisons and schedule results |
| Query schedules or find `gamePk` | `client.mlb.schedule` | One row per game | MLB Stats API | Game lists, daily slates, team schedules, and IDs for game endpoints |
| Query team rosters | `client.mlb.roster` | One row per roster entry | MLB Stats API | Active rosters and season roster snapshots |
| Query player bios | `client.mlb.people` | One row per person | MLB Stats API | Official player metadata and MLBAM IDs |
| Query player or team stats | `client.mlb.player_stats`, `client.mlb.team_stats` | Stat rows | MLB Stats API | Official hitting, pitching, and fielding stat groups |
| Query boxscore data | `client.mlb.game_boxscore`, `client.mlb.game_boxscore_stats` | Player-game or stat rows | MLB Stats API | Single-game lineups, participation, and boxscore stats |
| Query play-by-play data | `client.mlb.game_play_by_play`, `client.mlb.game_win_probability` | One row per play | MLB Stats API | Play logs, WPA, leverage, and event sequencing |
| Query game highlight videos | `client.mlb.game_highlights` | One row per highlight | MLB Stats API | Single-game video highlight metadata and MP4 URLs |
| Search MLB Film Room video clips | `client.mlb.film_room_search` | One row per video clip | MLB Film Room / Fastball Gateway | Video search by player, team, pitch type, exit velocity, and distance |
| Query live game feed data | `client.mlb.game_feed_live`, `client.mlb.game_linescore` | Event or inning rows | MLB Stats API | Live feed polling and inning-by-inning game state |
| Query official metadata | `client.mlb.teams`, `client.mlb.venues`, `client.mlb.divisions`, `client.mlb.leagues` | Dimension rows | MLB Stats API | Joining team, venue, division, and league metadata |
| Query transactions or draft records | `client.mlb.transactions`, `client.mlb.draft` | Transaction or pick rows | MLB Stats API | Roster movement and amateur draft analysis |
| Query standings | `client.mlb.standings` | One row per team-division season | MLB Stats API | Division standings with team records and games back |
| Query Lahman historical tables | `client.lahman.batting`, `client.lahman.pitching`, `client.lahman.people`, `client.lahman.teams_core`, and related helpers | Source table rows | Lahman | Historical offline analysis and stable table joins |
| Query Retrosheet files | `client.retrosheet.events`, `client.retrosheet.schedules`, `client.retrosheet.rosters`, `client.retrosheet.park_codes`, and game-log helpers | Source file rows | Retrosheet | Historical play-by-play, rosters, schedules, and park metadata |
| Query Baseball Reference WAR tables | `client.bref.bwar_bat`, `client.bref.bwar_pitch` | WAR table rows | Baseball Reference | bWAR leaderboards and historical WAR analysis |
| Query Baseball Reference game logs and splits | `client.bref.game_logs`, `client.bref.splits` | Game log or split rows | Baseball Reference | Single-season game logs and platoon/situational splits |
| Resolve player IDs | `client.lookup.playerid_lookup`, `client.lookup.playerid_reverse_lookup`, `client.lookup.chadwick_register` | Lookup rows | Chadwick register | Joining MLBAM, FanGraphs, Retrosheet, and other player identifiers |
| Query prospect rankings | `client.mlb.top_prospects`, `client.mlb.prospect_rankings` | Prospect rows | MLB Stats API | Official MLB pipeline prospect rankings by year, list type, or team |

## Provider Pages & Schemas

- [Statcast / Savant](reference/statcast.md)
- [FanGraphs](reference/fangraphs.md)
- [MLB Stats API](reference/mlb_api.md)
- [Lookups & Mappings](reference/lookups.md)
- [Baseball Reference](reference/bref.md)
- [Lahman](reference/lahman.md)
- [Retrosheet](reference/retrosheet.md)

## Operational Guides

- [Error Handling & Production Resilience](guides/error_handling.md)
- [Caching & Storage Guide](guides/caching.md)
- [Data Visualization Guide](guides/plotting.md)
