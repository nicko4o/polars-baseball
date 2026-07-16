> [!NOTE]
> 所有公開資料擷取 API 都是非同步函式。請在 async 環境中使用 `await`，或在指令碼中用 `asyncio.run()` 包裝呼叫。

# API 用途索引

用這頁依任務選 API。各 provider 頁面仍保留完整 signature、參數、範例與 edge cases。

| 使用情境 | 推薦 API | 回傳粒度 | 來源 | 適合用途 |
| --- | --- | --- | --- | --- |
| 查日期區間逐球資料 | `statcast` | 每列一球 | Baseball Savant | 球種、球速、擊球品質與打席分析 |
| 查單一投手逐球資料 | `statcast_pitcher` | 每列一球 | Baseball Savant | 投手球種庫、pitch mix 與對戰結果分析 |
| 查單一打者逐球資料 | `statcast_batter` | 每列一球 | Baseball Savant | 打者對戰、揮棒、接觸與擊球品質分析 |
| 查單場逐球資料 | `statcast_single_game` | 每列一球 | Baseball Savant | 依 `game_pk` 拆解單場投球 |
| 查打者或投手排行榜 | `pb.savant.batter_expected_stats`, `pb.savant.pitcher_pitch_arsenal` 與相關 helper | 排行榜列 | Baseball Savant | 球季層級 Statcast leaderboard 指標 |
| 查 FanGraphs 球員排行榜 | `pb.fangraphs.batting`, `pb.fangraphs.pitching`, `pb.fangraphs.fielding` | 排行榜列 | FanGraphs | 球員打擊、投球、守備排行榜 |
| 查 FanGraphs 球隊排行榜 | `pb.fangraphs.team_batting`, `pb.fangraphs.team_pitching`, `pb.fangraphs.team_fielding` | 球隊排行榜列 | FanGraphs | 球隊層級球季比較 |
| 查賽程或找 `gamePk` | `pb.mlb.schedule` | 每列一場比賽 | MLB Stats API | 比賽列表、每日賽程、球隊賽程與 game endpoint ID |
| 查球隊名冊 | `pb.mlb.roster` | 每列一筆名冊資料 | MLB Stats API | active roster 與球季名冊 snapshot |
| 查球員基本資料 | `pb.mlb.people` | 每列一人 | MLB Stats API | 官方球員 metadata 與 MLBAM ID |
| 查球員或球隊統計 | `pb.mlb.player_stats`, `pb.mlb.team_stats` | 統計列 | MLB Stats API | 官方打擊、投球、守備統計群組 |
| 查 boxscore | `pb.mlb.game_boxscore`, `pb.mlb.game_boxscore_stats` | 球員比賽列或統計列 | MLB Stats API | 單場 lineup、出賽與 boxscore stats |
| 查 play-by-play | `pb.mlb.game_play_by_play`, `pb.mlb.game_win_probability` | 每列一個 play | MLB Stats API | play log、WPA、leverage 與事件順序 |
| 查即時比賽資料 | `pb.mlb.game_feed_live`, `pb.mlb.game_linescore` | 事件列或局數列 | MLB Stats API | live feed 輪詢與逐局比賽狀態 |
| 查官方維度資料 | `pb.mlb.teams`, `pb.mlb.venues`, `pb.mlb.divisions`, `pb.mlb.leagues` | 維度表列 | MLB Stats API | join 球隊、球場、分區與聯盟 metadata |
| 查交易或選秀 | `pb.mlb.transactions`, `pb.mlb.draft` | 交易列或選秀列 | MLB Stats API | 球員異動與業餘選秀分析 |
| 查戰績排名 | `standings` | 每列一隊一分區球季 | MLB Stats API | 分區戰績、勝敗與 games back |
| 查 Lahman 歷史表 | `batting`, `pitching`, `people`, `teams_core` 與相關 helper | 原始資料表列 | Lahman | 歷史離線分析與穩定表格 join |
| 查 Retrosheet 檔案 | `events`, `schedules`, `rosters`, `park_codes` 與 game-log helpers | 原始檔案列 | Retrosheet | 歷史逐球、名冊、賽程與球場 metadata |
| 查 Baseball Reference WAR 表 | `bwar_bat`, `bwar_pitch` | WAR 表列 | Baseball Reference | bWAR 排行榜與歷史 WAR 分析 |
| 解析球員 ID | `playerid_lookup`, `playerid_reverse_lookup`, `chadwick_register` | lookup 列 | Chadwick register | 串接 MLBAM、FanGraphs、Retrosheet 與其他球員 ID |
| 查新秀排名 | `top_prospects`, `prospect_rankings` | 新秀列 | Baseball Savant | 依年份或球員類型查 prospect list |

## Provider 頁面

- [Statcast](reference/statcast.md)
- [Statcast batter APIs](reference/statcast_batter.md)
- [Statcast pitcher APIs](reference/statcast_pitcher.md)
- [FanGraphs](reference/fangraphs.md)
- [MLB Stats API](reference/mlb_api.md)
- [Player ID Lookup](reference/playerid_lookup.md)
- [Standings](reference/standings.md)
- [Savant Gamefeed](reference/savant_gamefeed.md)
- [Prospect Rankings](reference/prospect_rankings.md)
