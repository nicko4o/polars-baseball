from typing import Protocol, runtime_checkable

import polars as pl

from polars_baseball.parsers.base import BaseParser
from polars_baseball.parsers.bref import BRefGameLogParser, BRefHTMLParser, parse_bref_dataset
from polars_baseball.parsers.fangraphs import FangraphsHTMLParser
from polars_baseball.parsers.mlb import MLBApiParser
from polars_baseball.parsers.savant import SavantCSVParser, parse_savant_leaderboard


@runtime_checkable
class Parser(Protocol):
    def parse(self, raw: str) -> pl.DataFrame: ...


__all__ = [
    "BaseParser",
    "BRefGameLogParser",
    "BRefHTMLParser",
    "FangraphsHTMLParser",
    "MLBApiParser",
    "Parser",
    "SavantCSVParser",
    "parse_bref_dataset",
    "parse_savant_leaderboard",
]
