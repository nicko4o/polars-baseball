"""Legacy BRef schema module.

Re-exports from polars_baseball._schemas.bref for backward compatibility.
"""

from polars_baseball._schemas.bref import (
    _FLOAT_COLUMNS,
    _INT_COLUMNS,
    BREF_NULL_VALUES,
    BREF_SCHEMA_OVERRIDES,
    coerce_bref_schema,
    get_bref_column_type,
    sanitize_and_coerce_bref,
    sanitize_bref_nulls,
)

__all__ = [
    "BREF_NULL_VALUES",
    "BREF_SCHEMA_OVERRIDES",
    "_FLOAT_COLUMNS",
    "_INT_COLUMNS",
    "coerce_bref_schema",
    "get_bref_column_type",
    "sanitize_and_coerce_bref",
    "sanitize_bref_nulls",
]
