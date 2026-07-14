from __future__ import annotations

from polars_baseball.exceptions import InvalidParameterError

_PITCH_PAIRS: list[tuple[str, str]] = [
    ("FF", "4-Seamer"),
    ("CU", "Curveball"),
    ("CH", "Changeup"),
    ("FC", "Cutter"),
    ("EP", "Eephus"),
    ("FO", "Forkball"),
    ("KN", "Knuckleball"),
    ("KC", "Knuckle-curve"),
    ("SC", "Screwball"),
    ("SI", "Sinker"),
    ("SL", "Slider"),
    ("FS", "Splitter"),
    ("FT", "2-Seamer"),
    ("ST", "Sweeper"),
    ("SV", "Slurve"),
    ("SIFT", "Sinker"),
    ("CUKC", "Curveball"),
    ("ALL", "All"),
]


_pitch_code_to_name: dict[str, str] = dict(_PITCH_PAIRS)

_pitch_name_to_code: dict[str, str] = {}
for _code, _name in _PITCH_PAIRS:
    _pitch_name_to_code.setdefault(_code, _code)
    _pitch_name_to_code.setdefault(_name.upper(), _code)

pitch_codes = [p[0] for p in _PITCH_PAIRS]
pitch_names = [p[1] for p in _PITCH_PAIRS]


def norm_pitch_code(pitch: str, to_word: bool = False) -> str:
    code = _pitch_name_to_code.get(pitch.upper())
    if code is None:
        raise InvalidParameterError(f"{pitch} is not a valid pitch!")
    if to_word:
        return _pitch_code_to_name.get(code, code)
    return code
