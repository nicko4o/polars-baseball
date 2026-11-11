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


def safe_child_dict(parent: Mapping[str, object] | None, key: str) -> JsonObject:
    if not isinstance(parent, Mapping):
        return {}
    child = parent.get(key)
    return cast(JsonObject, child) if isinstance(child, dict) else {}


def to_int(val: object) -> int | None:
    if val is None or val == "":
        return None
    if isinstance(val, int) and not isinstance(val, bool):
        return val
    try:
        return int(float(str(val)))
    except (ValueError, TypeError):
        return None


def to_float(val: object) -> float | None:
    if val is None or val == "":
        return None
    if isinstance(val, (int, float)) and not isinstance(val, bool):
        return float(val)
    try:
        return float(str(val))
    except (ValueError, TypeError):
        return None


def to_str(val: object) -> str | None:
    if val is None:
        return None
    s = str(val).strip()
    return s if s else None
