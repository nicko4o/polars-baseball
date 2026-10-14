"""Convenience namespace for Baseball Reference endpoints."""

from polars_baseball.apis.bref import (
    bref_game_logs as game_logs,
    bref_splits as splits,
    bwar_bat,
    bwar_pitch,
)

__all__ = [
    "bwar_bat",
    "bwar_pitch",
    "game_logs",
    "splits",
]
