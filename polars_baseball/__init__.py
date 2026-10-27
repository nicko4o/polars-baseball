import logging as _logging

from polars_baseball import bref, fangraphs, lahman, lookup, mlb, retrosheet, savant
from polars_baseball.client import BaseballClient
from polars_baseball.enums import KeyType
from polars_baseball.enums.position import Position

__version__ = "0.28.0"

_logging.getLogger("polars_baseball").addHandler(_logging.NullHandler())

__all__ = [
    "BaseballClient",
    "KeyType",
    "Position",
    "__version__",
    "bref",
    "fangraphs",
    "lahman",
    "lookup",
    "mlb",
    "retrosheet",
    "savant",
]

for _pkg in ("client", "enums", "exceptions", "gateways", "parsers"):
    globals().pop(_pkg, None)
del _pkg
