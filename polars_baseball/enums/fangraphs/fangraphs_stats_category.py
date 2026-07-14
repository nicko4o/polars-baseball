from enum import unique

from ..enum_base import EnumBase


@unique
class FangraphsStatsCategory(EnumBase):
    BATTING = "bat"
    FIELDING = "fld"
    PITCHING = "pit"
    RELIEVERS = "rel"
    STARTERS = "sta"
