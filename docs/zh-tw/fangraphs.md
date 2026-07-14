> [!NOTE]
> 所有公開資料擷取 API 都是非同步函式。請在 async 環境中使用 `await`，或在指令碼中用 `asyncio.run()` 包裝呼叫。

# FanGraphs 資料擷取

FanGraphs 資料透過單一 `fg_data(request: FanGraphsRequest)` 函式與 `FanGraphsRequest` frozen dataclass 取得。

## `FanGraphsRequest`

| 欄位 | 型別 | 預設值 | 說明 |
| --- | --- | --- | --- |
| `start_season` | `int` | 必填 | 起始球季。 |
| `end_season` | `int \| None` | `start_season` | 結束球季。 |
| `stats_category` | `FangraphsStatsCategory` | `BATTING` | 要取得的資料類別。 |
| `league` | `FangraphsLeague \| str` | `ALL` | 聯盟篩選。字串（如 `"AL"`）會自動解析。 |
| `month` | `FangraphsMonth \| str` | `ALL` | 月份篩選；`ALL` 代表不篩選。 |
| `position` | `FangraphsPositions \| str` | `ALL` | 守位篩選。 |
| `stat_columns` | `str \| list[str]` | `ALL` | 要回傳的欄位。 |
| `qual` | `int \| None` | `None` | 最低出賽門檻。`None` = FG 預設。 |
| `split_seasons` | `bool` | `True` | `True` = 逐季資料；`False` = 彙總。 |
| `on_active_roster` | `bool` | `False` | `True` 時只回傳現役名單。 |
| `minimum_age` / `maximum_age` | `int` | `0` / `100` | 年齡範圍。 |
| `team` | `str` | `""` | 球隊篩選。 |
| `max_results` | `int` | `1_000_000` | 最大回傳列數。 |

可使用 factory 方法快速建立請求：`FanGraphsRequest.batting(start_season=2019)`、`.pitching(start_season=2019)`、`.team_batting(start_season=2019)` 等。

## 範例

```python
import asyncio
import polars_baseball as bp

async def main() -> None:
    batting = await bp.fg_data(bp.FanGraphsRequest.batting(start_season=2019))
    pitching = await bp.fg_data(bp.FanGraphsRequest.pitching(start_season=2019))
    team_batting = await bp.fg_data(bp.FanGraphsRequest.team_batting(start_season=2019))
    team_fielding = await bp.fg_data(bp.FanGraphsRequest.team_fielding(start_season=2019))
    team_pitching = await bp.fg_data(bp.FanGraphsRequest.team_pitching(start_season=2019))
    print(batting.head())
    print(pitching.head())
    print(team_batting.head())
    print(team_fielding.head())
    print(team_pitching.head())

if __name__ == "__main__":
    asyncio.run(main())
```
