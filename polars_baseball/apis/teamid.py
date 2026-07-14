from importlib.resources import files as resources_files
from pathlib import Path

import polars as pl

from polars_baseball._schema_utils import validate_and_cast_schema
from polars_baseball.exceptions import ServerError

# Team ID schemas
TEAM_IDS_REQUIRED: list[str] = ["lgID", "teamID", "yearID"]
TEAM_IDS_TYPES: dict[str, pl.DataType | type[pl.DataType]] = {
    "lgID": pl.String,
    "teamID": pl.String,
    "yearID": pl.Int64,
}

_DATA_DIR = Path(str(resources_files("polars_baseball").joinpath("data")))
_DATA_FILENAME = _DATA_DIR / "fangraphs_teams.csv"


def team_ids(season: int | None = None, league: str = "ALL") -> pl.DataFrame:
    """Fetch team identifiers from the bundled FanGraphs team data.

    Filters by season and/or league when provided.  Data sourced from
    ``polars_baseball/data/fangraphs_teams.csv``.

    Edge Cases:
        - Raises ``ServerError`` if the bundled CSV file is missing.
        - Returns empty DataFrame when no teams match the given season/league filters.
    """
    if not _DATA_FILENAME.exists():
        raise ServerError(f"Team ID data file not found at {_DATA_FILENAME}")

    df = pl.read_csv(_DATA_FILENAME)
    df = validate_and_cast_schema(df, TEAM_IDS_REQUIRED, TEAM_IDS_TYPES)

    if season is not None:
        df = df.filter(pl.col("yearID") == season)

    if league is not None and league.upper() != "ALL":
        df = df.filter(pl.col("lgID") == league.upper())

    return df
