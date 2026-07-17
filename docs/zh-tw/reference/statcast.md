> [!NOTE]
> 所有公開資料擷取 API 都是非同步函式。請在 async 環境中使用 `await`，或在指令碼中用 `asyncio.run()` 包裝呼叫。

# Baseball Savant / Statcast

Baseball Savant (Statcast) 排行榜、單球投球層級查詢、遊戲 Feed 以及新秀排名的說明與 API 參考手冊。

---

## 投球層級查詢 (Pitch-Level Queries)

擷取詳細的投球層級 Statcast 資料庫資料列。

### 函式

- `statcast(start_date: str | None = None, end_date: str | None = None, team: str | None = None, verbose: bool = True, parallel: bool = True) -> pl.DataFrame` (亦可透過 `savant.statcast` 呼叫)
- `statcast_single_game(game_pk: str | int) -> pl.DataFrame` (亦可透過 `savant.single_game` 呼叫)
- `statcast_batter(start_date: str, end_date: str, player_id: int) -> pl.DataFrame`
- `statcast_pitcher(start_date: str, end_date: str, player_id: int) -> pl.DataFrame`

### 參數

- `start_date` / `end_date`：`YYYY-MM-DD` 格式的日期區間。
- `team`：選填，球隊縮寫（例如 `"LAD"`、`"NYY"`、`"BOS"`）。
- `verbose`：為 `True` 時，列印擷取進度的提示訊息。
- `parallel`：為大型日期區間請求啟用並行下載。
- `game_pk`：MLBAM 遊戲識別碼。
- `player_id`：MLBAM 球員識別碼。

---

## 打者排行榜 (Batter Leaderboards)

擷取打者的累計表現統計數據。

### 函式

- `savant.batter_exitvelo_barrels(year: int, minBBE: int | str = "q") -> pl.DataFrame`
- `savant.batter_expected_stats(year: int, minPA: int | str = "q") -> pl.DataFrame`
- `savant.batter_percentile_ranks(year: int) -> pl.DataFrame`
- `savant.batter_pitch_arsenal(year: int, minPA: int = 25) -> pl.DataFrame`
- `savant.batter_run_value(year: int) -> pl.DataFrame`
- `savant.batter_bat_tracking(year: int, minSwings: int | str = "q") -> pl.DataFrame`
- `savant.exitvelo_barrels(year: int, player_type: str = "batter", minBBE: int | str = "q") -> pl.DataFrame`
- `savant.expected_stats(year: int, player_type: str = "batter", minPA: int | str = "q") -> pl.DataFrame`
- `savant.run_value(year: int, player_type: str = "batter") -> pl.DataFrame`
- `savant.bat_tracking(year: int, player_type: str = "batter", minSwings: int | str = "q") -> pl.DataFrame`

### 參數

- `year`：排行榜球季。
- `minPA`、`minBBE`、`minSwings`：最低出賽時間/事件門檻。可接受 `"q"` 代表符合資格（Qualified）的打者。
- `player_type`：`"batter"` 或 `"pitcher"`。

---

## 投手排行榜 (Pitcher Leaderboards)

擷取投手的累計表現統計數據。

### 函式

- `savant.pitcher_exitvelo_barrels(year: int, minBBE: int | str = "q") -> pl.DataFrame`
- `savant.pitcher_expected_stats(year: int, minPA: int | str = "q") -> pl.DataFrame`
- `savant.pitcher_pitch_arsenal(year: int, minP: int = 250, arsenal_type: ArsenalType = ArsenalType.AVG_SPEED) -> pl.DataFrame`
- `savant.pitcher_arsenal_stats(year: int, minPA: int = 25) -> pl.DataFrame`
- `savant.pitcher_pitch_movement(year: int, minP: int | str = "q", pitch_type: str = "FF") -> pl.DataFrame`
- `savant.pitcher_active_spin(year: int, minP: int = 250) -> pl.DataFrame`
- `savant.pitcher_percentile_ranks(year: int) -> pl.DataFrame`
- `savant.pitcher_spin_dir_comp(year: int, pitch_a: str = "FF", pitch_b: str = "CH", minP: int = 100, pitcher_pov: bool = True) -> pl.DataFrame`
- `savant.pitcher_run_value(year: int) -> pl.DataFrame`
- `savant.pitcher_bat_tracking(year: int, minSwings: int | str = "q") -> pl.DataFrame`
- `savant.pitch_arsenal_stats(year: int, player_type: str = "pitcher", min_count: int = 25) -> pl.DataFrame`
- `savant.pitch_tempo(year: int, min_pitches: int = 250) -> pl.DataFrame`

### 參數

- `minP`、`minPA`、`minBBE`、`minSwings`：最低投球數、打席數、擊球事件數或揮棒數門檻。
- `arsenal_type`：高階球種指標選擇（`ArsenalType.AVG_SPEED` 等）。
- `pitch_type`：球種代碼（例如 `"FF"` 代表四縫線快速球，`"SL"` 代表滑球）。
- `pitch_a` / `pitch_b`：要比較的球種。
- `pitcher_pov`：觀察視角。`True` 為投手視角，`False` 為打者視角。

---

## 守備排行榜 (Fielding Leaderboards)

擷取特製的守備排行榜指標。

### 函式

- `savant.outs_above_average(year: int, pos: str, min_att: int | str = "q", view: str = "Fielder") -> pl.DataFrame`
- `savant.fielding_run_value(year: int, pos: str, min_inn: int = 100) -> pl.DataFrame`
- `savant.outfield_directional_oaa(year: int, min_opp: int | str = "q") -> pl.DataFrame`
- `savant.outfield_catch_prob(year: int, min_opp: int | str = "q") -> pl.DataFrame`
- `savant.outfielder_jump(year: int, min_att: int | str = "q") -> pl.DataFrame`
- `savant.catcher_poptime(year: int, min_2b_att: int = 5, min_3b_att: int = 0) -> pl.DataFrame`
- `savant.catcher_framing(year: int, min_called_p: int | str = "q") -> pl.DataFrame`
- `savant.arm_strength(year: int, min_throws: int = 50) -> pl.DataFrame`
- `savant.catcher_throwing(year: int, min_att: int = 5) -> pl.DataFrame`
- `savant.catcher_stance(year: int) -> pl.DataFrame`
- `savant.catcher_blocking(year: int, min_chances: int = 100) -> pl.DataFrame`

### 參數

- `pos`：守備位置代碼（例如 `"CF"`、`"SS"`）。
- `min_att`、`min_opp`、`min_throws`、`min_inn`、`min_chances`：最低資格門檻。
- `view`：排行榜投影角度（例如預設為 `"Fielder"`）。

---

## 跑壘排行榜 (Running Leaderboards)

擷取跑壘、跑速與跑壘分段速度（splits）排行榜。

### 函式

- `savant.sprint_speed(year: int, min_opp: int = 10) -> pl.DataFrame`
- `savant.running_splits(year: int, min_opp: int = 5, raw_splits: bool = True) -> pl.DataFrame`
- `savant.baserunning_run_value(year: int, min_opp: int = 5) -> pl.DataFrame`
- `savant.base_stealing(year: int, min_attempts: int | str = "q") -> pl.DataFrame`

### 參數

- `min_opp`：最低跑壘機會次數（Sprinting Opportunities）。
- `raw_splits`：為 `True` 時，傳回原始分段時間；為 `False` 時，傳回分段百分位數。
- `min_attempts`：最低盜壘嘗試次數。

---

## 遊戲 Feed API (Gamefeed APIs)

擷取單場或批次遊戲的 JSON 資料集，並直接解析為 DataFrame。

### 函式

- `savant.gamefeed_exit_velocity(game_pk: int | str) -> pl.DataFrame`
- `savant.gamefeed_exit_velocity_many(game_pks: Sequence[int | str], parallel: bool = True) -> pl.DataFrame`
- `savant.gamefeed_pitch_data(game_pk: int | str) -> pl.DataFrame`
- `savant.gamefeed_pitch_data_many(game_pks: Sequence[int | str], parallel: bool = True) -> pl.DataFrame`

### 參數

- `game_pk`：MLB Advanced Media 遊戲識別碼。
- `game_pks`：要擷取並合併的遊戲 ID 列表。

---

## 新秀排名 (Prospect Rankings)

擷取大聯盟 Pipeline 新秀排名與 Pipeline 資料。

### 函式

- `prospect_rankings(list_type: str = "top100", year: int | None = None) -> pl.DataFrame`
- `top_prospects(team_name: str | None = None, player_type: str | None = None) -> pl.DataFrame`

### 參數

- `list_type`：欲查詢的清單類型（例如 `"top100"`、`"draft"`、`"international"`，或守備位置/球隊名稱）。
- `team_name`：目標球隊名稱（例如 `"bluejays"`、`"yankees"`）。
- `player_type`：`"pitchers"` 或 `"batters"`。

---

## 擊球仰角與噴角工具 (Spray Angle Utilities)

舊版 `add_spray_angle` pandas 工具已在第 2 版移除。衍生噴角（Spray Angle）應直接使用 Polars 表達式或 Python 數學計算：

```python
from math import atan2, pi

hc_x, hc_y = 125.42, 198.27
spray_angle = atan2(hc_x - 125.42, 198.27 - hc_y) * 180 / pi
```

### 範例分布

![Spray angle histograms](../../images/spray_angle_hists.png)

---

## 範例

```python
import asyncio
import polars_baseball as pb

async def main() -> None:
    # 1. 投球層級查詢
    game_df = await pb.statcast_single_game(529429)
    print("Single Game:", game_df.head(2))

    # 2. 排行榜
    expected = await pb.savant.batter_expected_stats(2024, minPA=100)
    arsenal = await pb.savant.pitcher_pitch_arsenal(2024, minP=250)
    print("Expected Stats:", expected.head(2))
    print("Pitcher Arsenal:", arsenal.head(2))

    # 3. 守備與跑壘
    oaa = await pb.savant.outs_above_average(2024, pos="CF", min_att="q")
    speed = await pb.savant.sprint_speed(2019, min_opp=50)
    print("OAACF:", oaa.head(2))
    print("Sprint Speed:", speed.head(2))

    # 4. 遊戲 Feed
    exit_velocity = await pb.savant.gamefeed_exit_velocity(745585)
    print("Gamefeed EV:", exit_velocity.head(2))

    # 5. 新秀排名
    prospects = await pb.prospect_rankings("top100")
    print("Prospects:", prospects.head(2))

if __name__ == "__main__":
    asyncio.run(main())
```
