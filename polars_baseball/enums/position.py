from __future__ import annotations

from enum import Enum

from polars_baseball.exceptions import InvalidParameterError

_POSITION_PAIRS: list[tuple[str, str]] = [
    ("IF", "Infield"),
    ("OF", "Outfield"),
    ("C", "Catcher"),
    ("1B", "First Base"),
    ("2B", "Second Base"),
    ("3B", "Third Base"),
    ("SS", "Shortstop"),
    ("LF", "Left Field"),
    ("CF", "Center Field"),
    ("RF", "Right Field"),
    ("ALL", "All"),
]


class Position(str, Enum):
    IF = "IF"
    OF = "OF"
    C = "C"
    FIRST_BASE = "1B"
    SECOND_BASE = "2B"
    THIRD_BASE = "3B"
    SS = "SS"
    LF = "LF"
    CF = "CF"
    RF = "RF"
    ALL = "ALL"


position_codes = [p[0] for p in _POSITION_PAIRS]
position_names = [p[1] for p in _POSITION_PAIRS]

POS_CODE_TO_NUMERIC: dict[str, str] = {code: str(num) for num, code in enumerate(position_codes[2:10], start=2)}

_pos_name_to_code: dict[str, str] = {}
for _code, _name in _POSITION_PAIRS:
    _pos_name_to_code[_code] = _code
    _pos_name_to_code[_name.upper()] = _code

_pos_code_to_name: dict[str, str] = dict(_POSITION_PAIRS)


def pos_to_numeric(pos: int | str) -> str:
    return norm_positions(pos, to_numeric=True)


def norm_positions(pos: int | str, to_word: bool = False, to_numeric: bool = False) -> str:
    pos_str = str(pos)

    if pos_str.lower() == "all":
        return ""

    if pos_str in POS_CODE_TO_NUMERIC.values():
        return pos_str

    code = _pos_name_to_code.get(pos_str.upper())
    if code is None:
        raise InvalidParameterError(f"{pos} is not a valid position!")

    if to_word:
        return _pos_code_to_name.get(code, code).lower()

    if to_numeric and code not in ("IF", "OF"):
        return POS_CODE_TO_NUMERIC.get(code, code)

    return code
