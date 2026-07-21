from enum import Enum
from typing import TypeVar

from polars_baseball.exceptions import InvalidParameterError

_T = TypeVar("_T", bound="EnumBase")


class EnumBase(Enum):
    @classmethod
    def values(enum_class: type[_T]) -> list[object]:
        return [x.value for x in enum_class]

    @classmethod
    def parse(enum_class: type[_T], value: str) -> _T:
        parsed: _T | None = enum_class.safe_parse(value)

        if parsed is None:
            raise InvalidParameterError(
                f"Invalid value of '{value}'. Values must be a valid member of the enum: {enum_class.__name__}"
            )

        return parsed

    @classmethod
    def safe_parse(enum_class: type[_T], value: str) -> _T | None:
        try:
            return enum_class[value]
        except KeyError:
            # Not found by name, fall through to value-based lookup below.
            pass

        parsed: _T | None = enum_class.safe_parse_by_value(value)

        return parsed

    @classmethod
    def safe_parse_by_value(enum_class: type[_T], value: object) -> _T | None:
        values = enum_class.values()

        matched = [x for x in values if str(x).upper() == str(value).upper()]

        if matched:
            return enum_class(matched[0])

        return None
