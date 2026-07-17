> [!NOTE]
> All public data-fetching APIs are asynchronous. Use `await` inside an async environment, or wrap calls with `asyncio.run()` in scripts.

# API Use-Case Index

Use this page to choose an API by task. Provider-specific pages still hold the detailed signatures, arguments, examples, and edge cases.

| Use case | Recommended API | Output grain | Source | Best for |
| --- | --- | --- | --- | --- |
| Query pitch-level data for a date range | `statcast` | One row per pitch | Baseball Savant | Pitch mix, velocity, batted-ball, and plate appearance analysis |
| Query pitch-level data for one pitcher | `statcast_pitcher` | One row per pitch | Baseball Savant | Pitcher arsenal, pitch mix, and opponent outcome analysis |
| Query pitch-level data for one batter | `statcast_batter` | One row per pitch | Baseball Savant | Batter matchup, swing, contact, and batted-ball analysis |
| Query pitch-level data for one game | `statcast_single_game` | One row per pitch | Baseball Savant | Single-game pitch breakdowns by `game_pk` |
| Query batter or pitcher leaderboards | `pb.savant.batter_expected_stats`, `pb.savant.pitcher_pitch_arsenal`, and related helpers | Leaderboard rows | Baseball Savant | Season-level Statcast leaderboard metrics |
| Query FanGraphs player leaderboards | `pb.fangraphs.batting`, `pb.fangraphs.pitching`, `pb.fangraphs.fielding` | Leaderboard rows | FanGraphs | Player batting, pitching, and fielding leaderboards |
| Query FanGraphs team leaderboards | `pb.fangraphs.team_batting`, `pb.fangraphs.team_pitching`, `pb.fangraphs.team_fielding` | Team leaderboard rows | FanGraphs | Team-level season comparisons |
| Query schedules or find `gamePk` | `pb.mlb.schedule` | One row per game | MLB Stats API | Game lists, daily slates, team schedules, and IDs for game endpoints |
| Query team rosters | `pb.mlb.roster` | One row per roster entry | MLB Stats API | Active rosters and season roster snapshots |
| Query player bios | `pb.mlb.people` | One row per person | MLB Stats API | Official player metadata and MLBAM IDs |
| Query player or team stats | `pb.mlb.player_stats`, `pb.mlb.team_stats` | Stat rows | MLB Stats API | Official hitting, pitching, and fielding stat groups |
| Query boxscore data | `pb.mlb.game_boxscore`, `pb.mlb.game_boxscore_stats` | Player-game or stat rows | MLB Stats API | Single-game lineups, participation, and boxscore stats |
| Query play-by-play data | `pb.mlb.game_play_by_play`, `pb.mlb.game_win_probability` | One row per play | MLB Stats API | Play logs, WPA, leverage, and event sequencing |
| Query live game feed data | `pb.mlb.game_feed_live`, `pb.mlb.game_linescore` | Event or inning rows | MLB Stats API | Live feed polling and inning-by-inning game state |
| Query official metadata | `pb.mlb.teams`, `pb.mlb.venues`, `pb.mlb.divisions`, `pb.mlb.leagues` | Dimension rows | MLB Stats API | Joining team, venue, division, and league metadata |
| Query transactions or draft records | `pb.mlb.transactions`, `pb.mlb.draft` | Transaction or pick rows | MLB Stats API | Roster movement and amateur draft analysis |
| Query standings | `standings` | One row per team-division season | MLB Stats API | Division standings with team records and games back |
| Query Lahman historical tables | `batting`, `pitching`, `people`, `teams_core`, and related helpers | Source table rows | Lahman | Historical offline analysis and stable table joins |
| Query Retrosheet files | `events`, `schedules`, `rosters`, `park_codes`, and game-log helpers | Source file rows | Retrosheet | Historical play-by-play, rosters, schedules, and park metadata |
| Query Baseball Reference WAR tables | `bwar_bat`, `bwar_pitch` | WAR table rows | Baseball Reference | bWAR leaderboards and historical WAR analysis |
| Resolve player IDs | `playerid_lookup`, `playerid_reverse_lookup`, `chadwick_register` | Lookup rows | Chadwick register | Joining MLBAM, FanGraphs, Retrosheet, and other player identifiers |
| Query prospect rankings | `top_prospects`, `prospect_rankings` | Prospect rows | Baseball Savant | Prospect lists and rankings by year or player type |

## Provider Pages

- [Statcast / Savant](reference/statcast.md)
- [FanGraphs](reference/fangraphs.md)
- [MLB Stats API](reference/mlb_api.md)
- [Lookups & Mappings](reference/lookups.md)
- [Baseball Reference](reference/bref.md)
