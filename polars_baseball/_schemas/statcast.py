"""Canonical schema definitions for Statcast compiled dataset partitions.

The canonical type mapping pins every known Statcast CSV column to a single
stable dtype so that ``pl.scan_parquet(..., hive_partitioning=True)`` across
multiple year partitions never hits cross-year dtype conflicts.
"""

from typing import Final

import polars as pl

STATCAST_CANONICAL_TYPES: Final[dict[str, pl.DataType | type[pl.DataType]]] = {
    "pitch_type": pl.String,
    "game_date": pl.String,
    "release_speed": pl.Float64,
    "release_pos_x": pl.Float64,
    "release_pos_z": pl.Float64,
    "player_name": pl.String,
    "batter": pl.Int64,
    "pitcher": pl.Int64,
    "events": pl.String,
    "description": pl.String,
    "spin_dir": pl.String,
    "spin_rate_deprecated": pl.String,
    "break_angle_deprecated": pl.String,
    "break_length_deprecated": pl.String,
    "zone": pl.Int64,
    "des": pl.String,
    "game_type": pl.String,
    "stand": pl.String,
    "p_throws": pl.String,
    "home_team": pl.String,
    "away_team": pl.String,
    "type": pl.String,
    "hit_location": pl.Float64,
    "bb_type": pl.String,
    "balls": pl.Int64,
    "strikes": pl.Int64,
    "game_year": pl.Int64,
    "pfx_x": pl.Float64,
    "pfx_z": pl.Float64,
    "plate_x": pl.Float64,
    "plate_z": pl.Float64,
    "on_3b": pl.Float64,
    "on_2b": pl.Float64,
    "on_1b": pl.Float64,
    "outs_when_up": pl.Int64,
    "inning": pl.Int64,
    "inning_topbot": pl.String,
    "hc_x": pl.Float64,
    "hc_y": pl.Float64,
    "tfs_deprecated": pl.String,
    "tfs_zulu_deprecated": pl.String,
    "fielder_2": pl.Int64,
    "umpire": pl.String,
    "sv_id": pl.String,
    "vx0": pl.Float64,
    "vy0": pl.Float64,
    "vz0": pl.Float64,
    "ax": pl.Float64,
    "ay": pl.Float64,
    "az": pl.Float64,
    "sz_top": pl.Float64,
    "sz_bot": pl.Float64,
    "hit_distance_sc": pl.Float64,
    "launch_speed": pl.Float64,
    "launch_angle": pl.Float64,
    "effective_speed": pl.Float64,
    "release_spin_rate": pl.Float64,
    "release_extension": pl.Float64,
    "game_pk": pl.Int64,
    "pitcher_duplicated_0": pl.Int64,
    "fielder_2_duplicated_0": pl.Int64,
    "fielder_3": pl.Int64,
    "fielder_4": pl.Int64,
    "fielder_5": pl.Int64,
    "fielder_6": pl.Int64,
    "fielder_7": pl.Int64,
    "fielder_8": pl.Int64,
    "fielder_9": pl.Int64,
    "release_pos_y": pl.Float64,
    "estimated_ba_using_speedangle": pl.Float64,
    "estimated_woba_using_speedangle": pl.Float64,
    "woba_value": pl.Float64,
    "woba_denom": pl.Float64,
    "babip_value": pl.Float64,
    "iso_value": pl.Float64,
    "launch_speed_angle": pl.Float64,
    "at_bat_number": pl.Int64,
    "pitch_number": pl.Int64,
    "pitch_name": pl.String,
    "home_score": pl.Int64,
    "away_score": pl.Int64,
    "bat_score": pl.Int64,
    "fld_score": pl.Int64,
    "post_away_score": pl.Int64,
    "post_home_score": pl.Int64,
    "post_bat_score": pl.Int64,
    "post_fld_score": pl.Int64,
    "if_fielding_alignment": pl.String,
    "of_fielding_alignment": pl.String,
}


def normalize_statcast_partition(df: pl.DataFrame) -> pl.DataFrame:
    """Fill missing canonical columns with null and cast known columns.

    Note:
        Guarantees a stable, fully-typed schema before writing a compiled
        dataset partition so cross-year ``scan_parquet`` never hits dtype conflicts.
        Non-canonical columns are passed through untouched.
    """
    if df.is_empty() and not df.columns:
        return df
    missing = [col for col in STATCAST_CANONICAL_TYPES if col not in df.columns]
    if missing:
        df = df.with_columns(pl.lit(None, dtype=STATCAST_CANONICAL_TYPES[col]).alias(col) for col in missing)
    casts = [
        pl.col(col).cast(STATCAST_CANONICAL_TYPES[col], strict=False)
        for col in df.columns
        if col in STATCAST_CANONICAL_TYPES
    ]
    if not casts:
        return df
    return df.with_columns(casts)
