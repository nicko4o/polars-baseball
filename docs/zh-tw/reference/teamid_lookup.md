# Team ID Lookup

`team_ids(season: int | None = None, league: str = "ALL") -> pl.DataFrame`

回傳 FanGraphs、Retrosheet、Baseball Reference、Lahman 與 MLB team IDs 的對照資料。

## 參數

- `season`：選用球季年份。省略時回傳所有球季的 mapping。
- `league`：選用聯盟篩選。預設為 `ALL`。

## 範例

```python
import asyncio

import polars as pl
from polars_baseball import FanGraphsRequest, fg_data
from polars_baseball.apis.teamid import team_ids

async def main() -> None:
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
    print(joined_df.head())

if __name__ == "__main__":
    asyncio.run(main())
```
