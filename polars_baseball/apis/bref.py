import warnings
from typing import Literal

import polars as pl

from polars_baseball._config import BREF_ROOT
from polars_baseball._schema_utils import validate_and_cast_schema
from polars_baseball.context import BaseballContext
from polars_baseball.gateways.bref import BRefGateway

# BWAR batting schema
BWAR_BAT_REQUIRED: list[str] = ["name_common", "mlb_ID", "player_ID", "year_ID", "team_ID"]
BWAR_BAT_TYPES: dict[str, pl.DataType | type[pl.DataType]] = {
    "name_common": pl.String,
    "mlb_ID": pl.String,
    "player_ID": pl.String,
    "year_ID": pl.Int64,
    "team_ID": pl.String,
    "stint_ID": pl.Int64,
    "lg_ID": pl.String,
    "pitcher": pl.String,
    "G": pl.Int64,
    "PA": pl.Int64,
    "salary": pl.Float64,
    "runs_above_avg": pl.Float64,
    "runs_above_avg_off": pl.Float64,
    "runs_above_avg_def": pl.Float64,
    "WAR_rep": pl.Float64,
    "WAA": pl.Float64,
    "WAR": pl.Float64,
}

# BWAR pitching schema
BWAR_PITCH_REQUIRED: list[str] = ["name_common", "mlb_ID", "player_ID", "year_ID", "team_ID"]
BWAR_PITCH_TYPES: dict[str, pl.DataType | type[pl.DataType]] = {
    "name_common": pl.String,
    "mlb_ID": pl.String,
    "player_ID": pl.String,
    "year_ID": pl.Int64,
    "team_ID": pl.String,
    "stint_ID": pl.Int64,
    "lg_ID": pl.String,
    "G": pl.Int64,
    "GS": pl.Int64,
    "RA": pl.Float64,
    "xRA": pl.Float64,
    "BIP": pl.Int64,
    "BIP_perc": pl.Float64,
    "salary": pl.Float64,
    "ERA_plus": pl.Int64,
    "WAR_rep": pl.Float64,
    "WAA": pl.Float64,
    "WAA_adj": pl.Float64,
    "WAR": pl.Float64,
}


async def _bwar_generic(
    stat_type: Literal["bat", "pitch"],
    required_cols: list[str],
    col_types: dict[str, pl.DataType | type[pl.DataType]],
    all_columns: bool = False,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    ctx = context or BaseballContext.default()
    url = f"{BREF_ROOT}/data/war_daily_{stat_type}.txt"
    gateway = BRefGateway(ctx)
    df = await gateway.get_dataset(url, params={"return_all": all_columns})
    df = validate_and_cast_schema(df, required_cols, col_types)
    if not all_columns:
        existing = [c for c in col_types if c in df.columns]
        df = df.select(existing)
    return df


async def bwar_bat(
    all_columns: bool = False,
    context: BaseballContext | None = None,
    *,
    return_all: bool | None = None,
) -> pl.DataFrame:
    """Fetch batting WAR from BRef.

    Note:
        When all_columns is False (default), returns only the columns defined
        in BWAR_BAT_REQUIRED. Pass all_columns=True for all available columns.
    """
    if return_all is not None:
        warnings.warn(
            "The 'return_all' parameter is deprecated; use 'all_columns' instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        all_columns = return_all
    return await _bwar_generic("bat", BWAR_BAT_REQUIRED, BWAR_BAT_TYPES, all_columns, context=context)


async def bwar_pitch(
    all_columns: bool = False,
    context: BaseballContext | None = None,
    *,
    return_all: bool | None = None,
) -> pl.DataFrame:
    """Fetch pitching WAR from BRef.

    Note:
        When all_columns is False (default), returns only the columns defined
        in BWAR_PITCH_REQUIRED. Pass all_columns=True for all available columns.
    """
    if return_all is not None:
        warnings.warn(
            "The 'return_all' parameter is deprecated; use 'all_columns' instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        all_columns = return_all
    return await _bwar_generic("pitch", BWAR_PITCH_REQUIRED, BWAR_PITCH_TYPES, all_columns, context=context)
