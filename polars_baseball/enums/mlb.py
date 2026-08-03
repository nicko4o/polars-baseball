from __future__ import annotations

from enum import StrEnum

from polars_baseball.exceptions import InvalidParameterError


class MlbStatsGroup(StrEnum):
    HITTING = "hitting"
    PITCHING = "pitching"
    FIELDING = "fielding"


class MlbRosterType(StrEnum):
    ACTIVE = "active"
    FULL = "full"
    FORTY_MAN = "40Man"
    ALL_TIME = "allTime"
    COACH = "coach"
    NON_ROSTER = "nonRoster"
    SPRING_ACTIVE = "springActive"
    SPRING_NON_ROSTER = "springNonRoster"
    TEAM = "team"


_ROSTER_TYPE_LOOKUP: dict[str, MlbRosterType] = {member.value.lower(): member for member in MlbRosterType}


def resolve_group(group: str | MlbStatsGroup) -> str:
    """Validate a stats group, returning its canonical upstream value."""
    if isinstance(group, MlbStatsGroup):
        return group.value
    try:
        return MlbStatsGroup(group.lower()).value
    except ValueError:
        raise InvalidParameterError(
            f"group must be one of: {', '.join(member.value for member in MlbStatsGroup)}."
        ) from None


def resolve_roster_type(roster_type: str | MlbRosterType) -> str:
    """Validate a roster type, returning its canonical upstream value."""
    if isinstance(roster_type, MlbRosterType):
        return roster_type.value
    member = _ROSTER_TYPE_LOOKUP.get(roster_type.lower())
    if member is None:
        raise InvalidParameterError(
            f"roster_type must be one of: {', '.join(member.value for member in MlbRosterType)}."
        )
    return member.value
