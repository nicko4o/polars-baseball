from collections.abc import Sequence
from enum import Enum
from typing import Final, cast

from ..enum_base import EnumBase

FG_COMMON: Final[str] = "c"
FG_LINE_BREAK: Final[str] = "-1"
FG_NAME: Final[str] = "0"
FG_TEAM: Final[str] = "1"
FG_SEASON: Final[str] = "2"


class FangraphsStatsBase(EnumBase):
    __COMMON_COLUMNS__ = [FG_NAME, FG_TEAM, FG_SEASON]

    @classmethod
    def ALL(cls) -> list["FangraphsStatsBase"]:  # pylint: disable=invalid-name
        def _sort_key(x: Enum) -> int:
            return int(x.value) if x.value.isdigit() else -2

        common_columns = [FG_COMMON] + cls.__COMMON_COLUMNS__
        column_list = list(set([column for column in cls if str(column.value) not in common_columns]))
        # Order the columns numerically, except for 'c' which always goes first
        column_list.sort(key=_sort_key)
        prepend: list[FangraphsStatsBase] = []
        # pylint: disable = no-member
        _common = cast("FangraphsStatsBase | None", getattr(cls, "COMMON", None))
        if _common is not None and _common not in column_list:
            prepend = [_common]
        return prepend + column_list

    @classmethod
    def replace_common(cls, enum_values: Sequence["FangraphsStatsBase"]) -> list["FangraphsStatsBase"]:
        stripped = [x for x in enum_values if str(x.value) not in cls.__COMMON_COLUMNS__]

        # pylint: disable = no-member
        _common = cast("FangraphsStatsBase", getattr(cls, "COMMON", None))
        return [_common] + stripped

    @classmethod
    def str_list(cls, enum_values: Sequence["FangraphsStatsBase"], replace_common: bool = True) -> str:
        stripped = cls.replace_common(enum_values) if replace_common else enum_values

        return ",".join([str(x.value) for x in stripped]).replace("c,c,", "c,")


def stat_list_to_str(values: Sequence[FangraphsStatsBase], replace_common: bool = True) -> str:
    if not values:
        return ""

    if not isinstance(values[0], FangraphsStatsBase):
        raise TypeError(f"Expected FangraphsStatsBase, got {type(values[0]).__name__}")

    obj_type = type(values[0])

    return obj_type.str_list(values, replace_common)
