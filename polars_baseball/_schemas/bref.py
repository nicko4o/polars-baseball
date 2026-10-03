"""Canonical schema definitions and coercion rules for Baseball Reference datasets."""

from collections.abc import Mapping
from typing import Final

import polars as pl

from polars_baseball.exceptions import UpstreamParseError

# Single Source of Truth for BRef Null Tokens
BREF_NULL_VALUES: Final[frozenset[str]] = frozenset({"---%", "---", "", "None", "nan", "none", "null"})

# Single Source of Truth for BRef Column Static Types
_INT_COLUMNS: Final[frozenset[str]] = frozenset(
    {
        "G",
        "Game",
        "NumPlayers",
        "AB",
        "R",
        "H",
        "2B",
        "3B",
        "HR",
        "RBI",
        "BB",
        "IBB",
        "SO",
        "HBP",
        "SH",
        "SF",
        "ROE",
        "GDP",
        "SB",
        "CS",
        "LOB",
        "PA",
        "BF",
        "Pit",
        "Str",
        "DoublePlays",
        "PO",
        "A",
        "E",
        "DP",
        "W",
        "L",
        "SV",
        "Hld",
        "Pitches",
        "Strikes",
        "DoP",
        "Val",
        "IR",
        "IS",
        "GB",
        "FB",
        "LD",
        "PU",
    }
)

_FLOAT_COLUMNS: Final[frozenset[str]] = frozenset(
    {
        "BA",
        "OBP",
        "SLG",
        "OPS",
        "ERA",
        "IP",
        "UQR",
        "WPA",
        "aLI",
        "WPA+",
        "WPA-",
        "RE24",
        "REW",
        "BLI",
        "pHat",
        "GSc",
        "Ctct",
        "StS",
        "StL",
    }
)

BREF_SCHEMA_OVERRIDES: Final[Mapping[str, pl.DataType | type[pl.DataType]]] = {
    "mlbID": pl.String,
    **{col: pl.Int64 for col in _INT_COLUMNS},
    **{col: pl.Float64 for col in _FLOAT_COLUMNS},
}

# BWAR batting schema
BWAR_BAT_REQUIRED: Final[list[str]] = ["name_common", "mlb_ID", "player_ID", "year_ID", "team_ID"]
BWAR_BAT_TYPES: Final[dict[str, pl.DataType | type[pl.DataType]]] = {
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
BWAR_PITCH_REQUIRED: Final[list[str]] = ["name_common", "mlb_ID", "player_ID", "year_ID", "team_ID"]
BWAR_PITCH_TYPES: Final[dict[str, pl.DataType | type[pl.DataType]]] = {
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


def get_bref_column_type(col: str) -> pl.DataType | type[pl.DataType] | None:
    """Resolve the static type for a BRef column, return None if unresolved."""
    if col == "mlbID":
        return pl.String
    if col in BREF_SCHEMA_OVERRIDES:
        return BREF_SCHEMA_OVERRIDES[col]

    if "_" not in col:
        return None

    parts = col.rsplit("_", 1)
    if len(parts) != 2:
        return None

    prefix, suffix = parts
    suffix_type = BREF_SCHEMA_OVERRIDES.get(suffix)
    if suffix_type is None:
        return None

    if suffix in ("Str", "Val", "Game", "W", "L", "E", "A", "R", "H", "DP", "IP"):
        prefix_lower = prefix.lower()
        if not any(kw in prefix_lower for kw in ("basic", "advanced", "value", "standard", "group2")):
            return None

    return suffix_type


def sanitize_bref_nulls(df: pl.DataFrame) -> pl.DataFrame:
    """Replace common BRef null tokens with null values in String columns."""
    if df.is_empty():
        return df

    null_exprs = [
        pl.when(pl.col(col).is_in(list(BREF_NULL_VALUES))).then(None).otherwise(pl.col(col)).alias(col)
        for col, dtype in df.schema.items()
        if dtype == pl.String
    ]
    return df.with_columns(null_exprs) if null_exprs else df


def _coerce_column_expr(col: str, target_type: pl.DataType | type[pl.DataType], series: pl.Series) -> pl.Expr:
    if target_type == pl.Float64 and series.dtype == pl.String:
        clean_series = pl.col(col).str.replace("%", "", literal=True)
        return (
            pl.when(pl.col(col).str.ends_with("%"))
            .then(clean_series.cast(pl.Float64, strict=False) / 100.0)
            .otherwise(pl.col(col).cast(pl.Float64, strict=False))
        )
    if target_type == pl.Int64 and series.dtype == pl.String:
        return pl.col(col).str.replace_all(",", "", literal=True).cast(pl.Int64, strict=False)
    return pl.col(col).cast(target_type, strict=False)


def coerce_bref_schema(df: pl.DataFrame) -> pl.DataFrame:
    """Coerce BRef column types based on static schema rules. Fail fast on error."""
    if df.is_empty():
        return df

    cols_to_cast = []
    for col in df.columns:
        if col == "Home":
            continue

        target_type = get_bref_column_type(col)
        if target_type is None:
            continue

        series = df[col]
        expr = _coerce_column_expr(col, target_type, series)
        cols_to_cast.append((col, target_type, series.null_count(), expr))

    if not cols_to_cast:
        return df

    eval_exprs = [expr.alias(col) for col, _, _, expr in cols_to_cast]
    try:
        temp_df = df.select(eval_exprs)
    except (ValueError, TypeError, pl.exceptions.ComputeError) as e:
        for col, target_type, _, expr in cols_to_cast:
            try:
                df.select(expr)
            except Exception as col_err:
                raise UpstreamParseError(
                    f"failed strict cast: Column '{col}' conversion to {target_type} failed: {col_err}"
                ) from col_err
        raise UpstreamParseError(f"failed strict cast: column conversion failed: {e}") from e

    for col, target_type, orig_nulls, _ in cols_to_cast:
        if temp_df[col].null_count() > orig_nulls:
            raise UpstreamParseError(f"failed strict cast: Column '{col}' contains invalid values for {target_type}.")

    return df.with_columns(eval_exprs)


def sanitize_and_coerce_bref(df: pl.DataFrame) -> pl.DataFrame:
    """Apply both null sanitization and schema coercion to a BRef DataFrame."""
    return coerce_bref_schema(sanitize_bref_nulls(df))
