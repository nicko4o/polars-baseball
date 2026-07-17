> [!NOTE]
> 除了 `team_ids` 外，所有公開資料擷取 API 都是非同步函式。請在 async 環境中使用 `await`，或在指令碼中用 `asyncio.run()` 包裝呼叫。

# 查詢與對照 (Lookups & Mappings)

提供球員查詢、在不同棒球數據庫之間進行球員/球隊 ID 對照，以及存取註冊表（Registry）的相關函式。

---

## 球員 ID 查詢 (Player ID Lookup)

尋找球員記錄並在 MLBAM、Retrosheet、FanGraphs、Baseball Reference 及其他主要來源之間進行 ID 對照。

### 函式

- `playerid_lookup(last: str, first: str | None = None, fuzzy: bool = False, ignore_accents: bool = False) -> pl.DataFrame`
- `player_search_list(player_list: list[tuple[str, str]]) -> pl.DataFrame`
- `get_lookup_table(save: bool = True) -> pl.DataFrame`

### 參數

- `last`：球員姓氏。
- `first`：選填，球員名字。若是常見姓氏，建議提供名字以縮小搜尋範圍。
- `fuzzy`：啟用模糊名稱比對，可容許拼字錯誤。
- `ignore_accents`：若為 `True`，在進行比對前會先將帶有重音的字元正規化（例如將 `ó` 轉為 `o`）。
- `player_list`：一個包含 `(last, first)` 元組的列表，用於進行批次查詢。
- `save`：若為 `True`，會將原始對照索引表快取至硬碟，以加速後續查詢。

---

## 球員 ID 逆向查詢 (Player ID Reverse Lookup)

從特定的資料庫 ID 列表反查球員註冊資訊。

### 函式

- `playerid_reverse_lookup(player_ids: list[int | str], key_type: KeyType = KeyType.MLBAM) -> pl.DataFrame`

### 參數

- `player_ids`：要查詢的 ID；MLBAM／FanGraphs 使用整數，BRef／Retrosheet 使用字串。
- `key_type`：輸入 ID 的資料庫命名空間。必須是 `KeyType` 列舉值：
  - `KeyType.MLBAM` (MLB Advanced Media / Statcast ID)
  - `KeyType.RETROSHEET` (Retrosheet ID)
  - `KeyType.FANGRAPHS` (FanGraphs ID)
  - `KeyType.BREF` (Baseball Reference ID)

---

## 球隊 ID 查詢 (Team ID Lookup)

傳回 FanGraphs、Retrosheet、Baseball Reference、Lahman 和 MLB 球隊 ID 之間的對照關係。

> [!NOTE]
> 與球員查詢 API 不同，`team_ids` 是一個**同步**函式，因為它是直接讀取專案內建的 CSV 檔案，而不需發送外部網路請求。

### 函式

- `team_ids(season: int | None = None, league: str = "ALL") -> pl.DataFrame`

### 參數

- `season`：選填，球季年份（例如 `2024`）。若省略，將傳回所有歷史球季的對照資料。
- `league`：選填，聯盟篩選（例如 `"AL"`、`"NL"`）。預設為 `"ALL"`。

---

## Chadwick 註冊表 (Chadwick Register)

擷取主 Chadwick Register 註冊表。該表包含通用的棒球識別符，可能包含從未進入大聯盟的歷史球員、總教練及其他相關人員。

### 函式

- `chadwick_register(save: bool = True) -> pl.DataFrame`

### 參數

- `save`：將編譯後的註冊表以 Parquet 格式快取至硬碟。設定為 `False` 可進行未快取的原始讀取。

---

## 範例

以下範例示範如何執行球員搜尋、逆向 ID 查詢、同步球隊 ID 合併以及獲取 Chadwick 註冊表：

```python
import asyncio
import polars as pl
from polars_baseball import (
    KeyType,
    FanGraphsRequest,
    fg_data,
    playerid_lookup,
    player_search_list,
    playerid_reverse_lookup,
    chadwick_register,
)
from polars_baseball.apis.teamid import team_ids

async def main() -> None:
    # 1. 球員搜尋與批次搜尋
    jones = await playerid_lookup("jones")
    judge = await playerid_lookup("judge", "aaron")
    players = await player_search_list([("judge", "aaron")])
    print("Player Search:", judge.head())

    # 2. 逆向查詢
    reversed_df = await playerid_reverse_lookup([592450], key_type=KeyType.MLBAM)
    print("Reverse Lookup:", reversed_df.head())

    # 3. 同步球隊 ID 對照並合併 FanGraphs 資料
    teams_df = team_ids(2019)
    batting_df = await fg_data(FanGraphsRequest.team_batting(start_season=2019))
    batting_df = batting_df.select([
        pl.col(column).alias(f"batting.{column}")
        for column in batting_df.columns
    ])
    joined_df = teams_df.join(
        batting_df,
        left_on=["yearID", "teamIDfg"],
        right_on=["batting.Season", "batting.teamid"],
        how="inner",
    )
    print("Joined Teams:", joined_df.head(2))

    # 4. Chadwick 註冊表
    register = await chadwick_register(save=True)
    print("Chadwick Register:", register.head(2))

if __name__ == "__main__":
    asyncio.run(main())
```
