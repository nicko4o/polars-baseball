from typing import Literal

import polars as pl

from polars_baseball._config import BREF_ROOT
from polars_baseball._schema_utils import validate_and_cast_schema
from polars_baseball._schemas.bref import (
    BWAR_BAT_REQUIRED,
    BWAR_BAT_TYPES,
    BWAR_PITCH_REQUIRED,
    BWAR_PITCH_TYPES,
)
from polars_baseball.context import BaseballContext
from polars_baseball.gateways.bref import BRefGateway


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
) -> pl.DataFrame:
    """Fetch batting WAR from BRef.

    Note:
        When all_columns is False (default), returns only the columns defined
        in BWAR_BAT_REQUIRED. Pass all_columns=True for all available columns.
    """
    return await _bwar_generic("bat", BWAR_BAT_REQUIRED, BWAR_BAT_TYPES, all_columns, context=context)


async def bwar_pitch(
    all_columns: bool = False,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch pitching WAR from BRef.

    Note:
        When all_columns is False (default), returns only the columns defined
        in BWAR_PITCH_REQUIRED. Pass all_columns=True for all available columns.
    """
    return await _bwar_generic("pitch", BWAR_PITCH_REQUIRED, BWAR_PITCH_TYPES, all_columns, context=context)
