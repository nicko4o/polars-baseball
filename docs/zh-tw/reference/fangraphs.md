> [!NOTE]
> 所有公開資料擷取 API 都是非同步函式。請在 async 環境中使用 `await`，或在指令碼中用 `asyncio.run()` 包裝呼叫。

# FanGraphs 資料擷取

從 FanGraphs 擷取球員與球隊排行榜的說明與 API 參考手冊。

---

## 快捷命名空間 (Namespace Helpers)

對於常見查詢，建議使用 `fangraphs` 命名空間下的快捷函式（例如 `pb.fangraphs.batting(...)`）。

### 函式

| 函式 | 說明 |
| --- | --- |
| `fangraphs.batting(start_season, ...)` | 球員打擊排行榜。 |
| `fangraphs.pitching(start_season, ...)` | 球員投球排行榜。 |
| `fangraphs.fielding(start_season, ...)` | 球員守備排行榜。 |
| `fangraphs.team_batting(start_season, ...)` | 球隊打擊排行榜。 |
| `fangraphs.team_pitching(start_season, ...)` | 球隊投球排行榜。 |
| `fangraphs.team_fielding(start_season, ...)` | 球隊守備排行榜。 |

### 參數

命名空間快捷函式直接接受 `FanGraphsRequest` 支援的所有欄位作為關鍵字引數（Keyword Arguments）。

---

## 進階查詢 (`fg_data`)

進階使用者可以手動建立 `FanGraphsRequest` 物件並將其直接傳入 `fg_data` 以執行高度客製化的查詢。

### 函式

- `fg_data(request: FanGraphsRequest) -> pl.DataFrame`

### `FanGraphsRequest` 屬性

可使用類別方法建立請求：`FanGraphsRequest.batting(...)`、`FanGraphsRequest.pitching(...)`、`FanGraphsRequest.team_batting(...)` 等。

| 欄位 | 型別 | 預設值 | 說明 |
| --- | --- | --- | --- |
| `start_season` | `int` | 必填 | 起始球季。 |
| `end_season` | `int \| None` | `start_season` | 結束球季。 |
| `stats_category` | `FangraphsStatsCategory` | `BATTING` | 要取得的資料類別。 |
| `league` | `FangraphsLeague \| str` | `ALL` | 聯盟篩選。字串（如 `"AL"`、`"NL"`）會自動解析。 |
| `month` | `FangraphsMonth \| str` | `ALL` | 月份/Split 篩選；`ALL` 代表不篩選。 |
| `position` | `FangraphsPositions \| str` | `ALL` | 守位篩選。 |
| `stat_columns` | `str \| list[str]` | `ALL` | 要回傳的欄位，或 `"ALL"` 使用預設欄位集。 |
| `qual` | `int \| None` | `None` | 最低出賽時間門檻。`None` 代表使用 FanGraphs 預設值。 |
| `split_seasons` | `bool` | `True` | `True` 傳回單季數據；`False` 將指定區間的數據進行累計彙整。 |
| `on_active_roster` | `bool` | `False` | 為 `True` 時，僅傳回現役名單（Active Roster）內的球員。 |
| `minimum_age` / `maximum_age` | `int` | `0` / `100` | 球員年齡篩選範圍。 |
| `team` | `str` | `""` | 球隊篩選。使用 `"0,ts"` 可取得彙總的球隊層級資料列。 |
| `max_results` | `int` | `1_000_000` | 最大回傳資料列數。 |

---

## 範例

以下範例示範如何使用快捷命名空間函式與自訂的 `FanGraphsRequest` 進行查詢：

```python
import asyncio
import polars_baseball as pb

async def main() -> None:
    # 1. 使用命名空間快捷函式
    batting = await pb.fangraphs.batting(start_season=2019)
    pitching = await pb.fangraphs.pitching(start_season=2019)
    team_batting = await pb.fangraphs.team_batting(start_season=2019)
    team_fielding = await pb.fangraphs.team_fielding(start_season=2019)
    team_pitching = await pb.fangraphs.team_pitching(start_season=2019)
    print("Namespace Batting:", batting.head(2))

    # 2. 使用 fg_data 與 FanGraphsRequest 進行進階查詢
    req_batting = pb.FanGraphsRequest.batting(start_season=2024)
    req_qualified = pb.FanGraphsRequest.batting(start_season=2023, qual=50)
    req_split = pb.FanGraphsRequest.batting(start_season=2020, end_season=2024, split_seasons=True)
    
    season_df = await pb.fg_data(req_batting)
    qualified_df = await pb.fg_data(req_qualified)
    split_df = await pb.fg_data(req_split)
    print("Advanced Query:", season_df.head(2))

if __name__ == "__main__":
    asyncio.run(main())
```
