"""Schema definitions for Baseball Savant data structures."""

from typing import Final

import polars as pl

SAVANT_PARK_FACTORS_REQUIRED: Final[tuple[str, ...]] = (
    "venue_id",
    "venue_name",
    "year",
)

SAVANT_PARK_FACTORS_TYPES: Final[dict[str, pl.DataType | type[pl.DataType]]] = {
    "venue_id": pl.Int64,
    "venue_name": pl.String,
    "team_id": pl.Int64,
    "team_name": pl.String,
    "year": pl.Int64,
    "year_range": pl.String,
    "bat_side": pl.String,
    "n_pa": pl.Int64,
    "park_factor": pl.Int64,
    "woba_factor": pl.Int64,
    "runs_factor": pl.Int64,
    "hr_factor": pl.Int64,
    "hits_factor": pl.Int64,
    "singles_factor": pl.Int64,
    "doubles_factor": pl.Int64,
    "triples_factor": pl.Int64,
    "so_factor": pl.Int64,
    "bb_factor": pl.Int64,
    "hard_hit_factor": pl.Int64,
}
