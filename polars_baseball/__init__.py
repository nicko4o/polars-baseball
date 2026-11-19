import logging as _logging

from polars_baseball import bref, fangraphs, lahman, lookup, mlb, retrosheet, savant
from polars_baseball.client import BaseballClient
from polars_baseball.enums import KeyType
from polars_baseball.enums.position import Position
from polars_baseball.exceptions import (
    CacheClearError,
    ClientError,
    InvalidParameterError,
    InvalidSchemaError,
    PolarsBaseballError,
    PolarsBaseballHttpClientError,
    PolarsBaseballHttpError,
    PolarsBaseballHttpServerError,
    PolarsBaseballTransportError,
    ServerError,
    UpstreamDataCorruptedError,
    UpstreamParseError,
    UpstreamStructureChangedError,
    UpstreamUnavailableError,
)

__version__ = "0.30.0"

_logging.getLogger("polars_baseball").addHandler(_logging.NullHandler())

__all__ = [
    "BaseballClient",
    "CacheClearError",
    "ClientError",
    "InvalidParameterError",
    "InvalidSchemaError",
    "KeyType",
    "PolarsBaseballError",
    "PolarsBaseballHttpClientError",
    "PolarsBaseballHttpError",
    "PolarsBaseballHttpServerError",
    "PolarsBaseballTransportError",
    "Position",
    "ServerError",
    "UpstreamDataCorruptedError",
    "UpstreamParseError",
    "UpstreamStructureChangedError",
    "UpstreamUnavailableError",
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
