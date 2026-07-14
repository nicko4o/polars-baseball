# Team ID Lookup

`team_ids(season: int | None = None, league: str = "ALL") -> pl.DataFrame`

Returns mappings between FanGraphs, Retrosheet, Baseball Reference, Lahman, and MLB team IDs.

## Arguments

- `season`: Optional season year. If omitted, mappings for all seasons are returned.
- `league`: Optional league filter. Defaults to `ALL`.

## Example

```python
import asyncio

import polars as pl
from polars_baseball import FanGraphsRequest, fg_data
from polars_baseball.apis.teamid import team_ids

async def main() -> None:
    teams_df = team_ids(2019)
    batting_df = await fg_data(FanGraphsRequest.team_batting(2019))
    batting_df = batting_df.select([
        pl.col(column).alias(f"batting.{column}")
        for column in batting_df.columns
    ])
    joined_df = teams_df.join(
        batting_df,
        left_on=["yearID", "teamIDfg"],
        right_on=["batting.Season", "batting.teamIDfg"],
        how="inner",
    )
    print(joined_df.head())

if __name__ == "__main__":
    asyncio.run(main())
```
