from collections.abc import Mapping
from typing import cast

import polars as pl

from polars_baseball._json_utils import child_mapping, expect_mapping
from polars_baseball.exceptions import InvalidSchemaError, UpstreamStructureChangedError


def validate_critical_columns_present(
    df: pl.DataFrame,
    critical_columns: set[str],
    label: str = "DataFrame",
) -> None:
    missing = critical_columns - set(df.columns)
    if missing:
        raise InvalidSchemaError(f"Missing critical columns in {label}: {missing}. Available: {sorted(df.columns)}")


def validate_next_data_structure(data: object, label: str = "FanGraphs NEXT_DATA") -> list[Mapping[str, object]]:
    expect_mapping(data, f"{label} root")
    root = cast(Mapping[str, object], data)
    root = child_mapping(root, "props", "props")
    root = child_mapping(root, "pageProps", "props.pageProps")
    root = child_mapping(root, "dehydratedState", "props.pageProps.dehydratedState")
    queries = root.get("queries")
    if not isinstance(queries, list):
        raise UpstreamStructureChangedError(
            f"Expected {label}.props.pageProps.dehydratedState.queries to be a list, got {type(queries).__name__}"
        )
    if not all(isinstance(q, Mapping) for q in queries):
        raise UpstreamStructureChangedError(
            f"Expected {label}.props.pageProps.dehydratedState.queries entries to be JSON objects."
        )
    return cast(list[Mapping[str, object]], queries)
