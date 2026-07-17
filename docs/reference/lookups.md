> [!NOTE]
> All public data-fetching APIs (except `team_ids`) are asynchronous. Use `await` inside an async environment, or wrap calls with `asyncio.run()` in scripts.

# Lookups & Mappings

Functions for looking up players, mapping player/team IDs across different baseball databases, and accessing registry tables.

---

## Player ID Lookup

Finds player records and maps IDs across MLBAM, Retrosheet, FanGraphs, Baseball Reference, and other major sources.

### Functions

- `playerid_lookup(last: str, first: str | None = None, fuzzy: bool = False, ignore_accents: bool = False) -> pl.DataFrame`
- `player_search_list(player_list: list[tuple[str, str]]) -> pl.DataFrame`
- `get_lookup_table(save: bool = True) -> pl.DataFrame`

### Arguments

- `last`: Player last name.
- `first`: Optional player first name. Narrowing down with a first name is recommended for common names.
- `fuzzy`: Enable fuzzy name matching for typos.
- `ignore_accents`: If `True`, normalizes accented characters (e.g. `ó` to `o`) before matching.
- `player_list`: A list of `(last, first)` tuples for performing batch lookups.
- `save`: If `True`, caches the raw lookup index mapping to disk for fast subsequent queries.

---

## Player ID Reverse Lookup

Finds player registry mappings from a list of source-specific database IDs.

### Functions

- `playerid_reverse_lookup(player_ids: list[int | str], key_type: KeyType = KeyType.MLBAM) -> pl.DataFrame`

### Arguments

- `player_ids`: IDs to look up. Use integers for MLBAM/FanGraphs and strings for BRef/Retrosheet.
- `key_type`: The source database namespace of the input IDs. Must be a `KeyType` enum value:
  - `KeyType.MLBAM` (MLB Advanced Media / Statcast ID)
  - `KeyType.RETROSHEET` (Retrosheet ID)
  - `KeyType.FANGRAPHS` (FanGraphs ID)
  - `KeyType.BREF` (Baseball Reference ID)

---

## Team ID Lookup

Returns team mapping identifiers between FanGraphs, Retrosheet, Baseball Reference, Lahman, and MLB team IDs.

> [!NOTE]
> Unlike player lookup APIs, `team_ids` is a **synchronous** function because it reads from a bundled CSV on disk rather than hitting external network APIs.

### Functions

- `team_ids(season: int | None = None, league: str = "ALL") -> pl.DataFrame`

### Arguments

- `season`: Optional season year (e.g. `2024`). If omitted, returns mappings across all historical seasons.
- `league`: Optional league filter (e.g. `"AL"`, `"NL"`). Defaults to `"ALL"`.

---

## Chadwick Register

Retrieves the master Chadwick Register database mapping. This registry contains general baseball identifiers and may include historical players, managers, and personnel who never played in the major leagues.

### Functions

- `chadwick_register(save: bool = True) -> pl.DataFrame`

### Arguments

- `save`: Cache the compiled register Parquet table to disk. Set `False` for an uncached boundary read.

---

## Example

The following example shows how to perform player searches, reverse ID lookups, synchronous team ID joins, and fetch the Chadwick register.

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
    # 1. Player search and batch search
    jones = await playerid_lookup("jones")
    judge = await playerid_lookup("judge", "aaron")
    players = await player_search_list([("judge", "aaron")])
    print("Player Search:", judge.head())

    # 2. Reverse lookup
    reversed_df = await playerid_reverse_lookup([592450], key_type=KeyType.MLBAM)
    print("Reverse Lookup:", reversed_df.head())

    # 3. Synchronous Team ID mapping joined with FanGraphs data
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

    # 4. Chadwick Register
    register = await chadwick_register(save=True)
    print("Chadwick Register:", register.head(2))

if __name__ == "__main__":
    asyncio.run(main())
```
