from .batting_data_enum import FangraphsBattingStats
from .fangraphs_stats_base import FangraphsStatsBase, stat_list_to_str
from .fangraphs_stats_category import FangraphsStatsCategory
from .fielding_data_enum import FangraphsFieldingStats
from .league import FangraphsLeague
from .month import FangraphsMonth
from .pitching_data_enum import FangraphsPitchingStats
from .positions import FangraphsPositions

FangraphsStatColumn = FangraphsBattingStats | FangraphsFieldingStats | FangraphsPitchingStats

__all__ = [
    "FangraphsBattingStats",
    "FangraphsStatsBase",
    "stat_list_to_str",
    "FangraphsStatsCategory",
    "FangraphsFieldingStats",
    "FangraphsLeague",
    "FangraphsMonth",
    "FangraphsPitchingStats",
    "FangraphsPositions",
    "FangraphsStatColumn",
    "stat_list_from_str",
]

_category_enum_map: dict[FangraphsStatsCategory, type[FangraphsStatColumn]] = {
    FangraphsStatsCategory.BATTING: FangraphsBattingStats,
    FangraphsStatsCategory.FIELDING: FangraphsFieldingStats,
    FangraphsStatsCategory.PITCHING: FangraphsPitchingStats,
    FangraphsStatsCategory.RELIEVERS: FangraphsPitchingStats,
    FangraphsStatsCategory.STARTERS: FangraphsPitchingStats,
}


def stat_list_from_str(
    stat_category: FangraphsStatsCategory, values: str | list[str] | list[FangraphsStatColumn]
) -> list[FangraphsStatColumn]:
    if not values:
        return []

    if isinstance(values, str):
        values = [values]

    obj_type = _category_enum_map[stat_category]

    if "ALL" in values or any(getattr(x, "name", None) == "ALL" for x in values):
        return obj_type.ALL()  # type: ignore

    stat_list: list[FangraphsStatColumn] = []
    for x in values:
        if isinstance(x, FangraphsStatsBase):
            stat_list.append(x)
        elif isinstance(x, str):
            stat_list.append(obj_type.parse(x.upper()))
        else:
            raise TypeError(f"Invalid stat column type: {type(x)}")

    return stat_list
