import logging as _logging

from polars_baseball import bref, fangraphs, lahman, lookup, mlb, retrosheet, savant
from polars_baseball.context import BaseballClient, BaseballContext, cleanup
from polars_baseball.enums import KeyType
from polars_baseball.enums.position import Position

__version__ = "0.25.0"

_logging.getLogger("polars_baseball").addHandler(_logging.NullHandler())

__all__ = [
    "BaseballClient",
    "BaseballContext",
    "KeyType",
    "Position",
    "__version__",
    "bref",
    "cleanup",
    "fangraphs",
    "lahman",
    "lookup",
    "mlb",
    "retrosheet",
    "savant",
]

for _pkg in ("apis", "context", "enums", "exceptions", "gateways", "parsers"):
    globals().pop(_pkg, None)
del _pkg
