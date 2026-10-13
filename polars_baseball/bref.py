"""Convenience namespace for Baseball Reference endpoints."""

from polars_baseball.apis.bref import (
    bref_game_logs as game_logs,
)
from polars_baseball.apis.bref import (
    bref_splits as splits,
)
from polars_baseball.apis.bref import (
    bwar_bat,
    bwar_pitch,
)

__all__ = [
    "bwar_bat",
    "bwar_pitch",
    "game_logs",
    "splits",
]
