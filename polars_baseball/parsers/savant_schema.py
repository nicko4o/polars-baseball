from collections.abc import Mapping

import polars as pl

SAVANT_SCHEMA_OVERRIDES: Mapping[str, pl.DataType | type[pl.DataType]] = {
    "pitcher": pl.Int64,
    "batter": pl.Int64,
    "player_id": pl.Int64,
    "year": pl.Int64,
    "release_speed": pl.Float64,
    "zone": pl.Int64,
    "balls": pl.Int64,
    "strikes": pl.Int64,
    "game_year": pl.Int64,
    "outs_when_up": pl.Int64,
    "inning": pl.Int64,
    "launch_speed": pl.Float64,
    "launch_angle": pl.Float64,
    "game_pk": pl.Int64,
    "bat_speed": pl.Float64,
    "swing_length": pl.Float64,
    "miss_distance": pl.Float64,
}
