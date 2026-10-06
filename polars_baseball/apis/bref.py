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


async def bref_game_logs(
    player_id: str,
    year: int,
    log_type: Literal["batting", "pitching"] = "batting",
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch Baseball Reference single-season game logs for a player.

    Args:
        player_id: BRef player identifier (e.g. 'troutmi01').
        year: Season year (e.g. 2024).
        log_type: Type of game log, either 'batting' or 'pitching'.
        context: Optional BaseballContext instance.

    Returns:
        DataFrame containing parsed game-by-game statistics.
    """
    from polars_baseball.exceptions import InvalidParameterError

    if not player_id:
        raise InvalidParameterError("player_id must not be empty.")
    if log_type not in ("batting", "pitching"):
        raise InvalidParameterError("log_type must be either 'batting' or 'pitching'.")
    ctx = context or BaseballContext.default()
    return await BRefGateway(ctx).get_game_logs(player_id, year, log_type)


async def bref_splits(
    player_id: str,
    year: int | None = None,
    pitching: bool = False,
    context: BaseballContext | None = None,
) -> list[pl.DataFrame]:
    """Fetch Baseball Reference platoon/situational splits for a player.

    Args:
        player_id: BRef player identifier (e.g. 'troutmi01').
        year: Season year, or None for career splits.
        pitching: True for pitching splits, False for batting splits.
        context: Optional BaseballContext instance.

    Returns:
        List of DataFrames [df_main, df_player_info, df_level] where:
        - df_main: DataFrame with main platoon/count splits.
        - df_player_info: Single-row DataFrame with biographical metadata (Position, Bats, Throws).
        - df_level: DataFrame with minor league level splits (if pitching), else empty.
    """
    from polars_baseball.exceptions import InvalidParameterError

    if not player_id:
        raise InvalidParameterError("player_id must not be empty.")
    ctx = context or BaseballContext.default()
    df_main, player_info, df_level = await BRefGateway(ctx).get_splits(player_id, year, pitching)
    df_info = pl.DataFrame(
        {
            "Position": [player_info.get("Position", "")],
            "Bats": [player_info.get("Bats", "")],
            "Throws": [player_info.get("Throws", "")],
        }
    )
    return [df_main, df_info, df_level]
