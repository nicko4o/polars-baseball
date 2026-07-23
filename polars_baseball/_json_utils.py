from collections.abc import Mapping
from typing import TypeAlias, cast

from polars_baseball.exceptions import UpstreamStructureChangedError

JsonObject: TypeAlias = dict[str, object]


def expect_mapping(value: object, label: str) -> None:
    if not isinstance(value, Mapping):
        raise UpstreamStructureChangedError(
            f"Expected {label} to be a Mapping (JSON object), got {type(value).__name__}"
        )


def child_mapping(parent: Mapping[str, object], key: str, label: str) -> Mapping[str, object]:
    child = parent.get(key)
    if not isinstance(child, Mapping):
        raise UpstreamStructureChangedError(
            f"Expected {label} to be a Mapping (JSON object), got {type(child).__name__}"
        )
    return cast(Mapping[str, object], child)
