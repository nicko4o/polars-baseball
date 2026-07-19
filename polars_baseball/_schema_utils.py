from collections.abc import Sequence

import polars as pl

from polars_baseball.exceptions import InvalidSchemaError


def validate_and_cast_schema(
    df: pl.DataFrame,
    required_cols: Sequence[str],
    type_mapping: dict[str, pl.DataType | type[pl.DataType]],
) -> pl.DataFrame:
    """Validate required columns exist and cast to target types.

    Note:
        Returns the DataFrame unchanged when it is empty (no rows to
        validate). Raises InvalidSchemaError when required columns are
        missing or when casting fails.
    """
    if df.is_empty():
        return df

    missing_cols = [col for col in required_cols if col not in df.columns]
    if missing_cols:
        raise InvalidSchemaError(f"Missing required columns from upstream data: {missing_cols}")

    cast_exprs = [pl.col(col).cast(type_mapping[col]) for col in type_mapping if col in df.columns]
    if not cast_exprs:
        return df

    try:
        return df.with_columns(cast_exprs)
    except Exception as e:
        raise InvalidSchemaError(f"Failed to cast DataFrame columns to target schema: {e}") from e
