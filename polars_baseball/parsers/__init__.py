from typing import Protocol, runtime_checkable

import polars as pl

from polars_baseball.parsers._strategy import (
    ChainResult,
    ExtractionStrategy,
    ProbeResult,
    ProviderChain,
    StructureFingerprint,
)
from polars_baseball.parsers.base import BaseParser
from polars_baseball.parsers.bref import BRefGameLogParser
from polars_baseball.parsers.bref_standard_strategy import (
    BRefCSVExportStrategy,
    BRefGameLogStrategy,
    BRefStandardStrategy,
)
from polars_baseball.parsers.fangraphs_next_data_strategy import (
    FangraphsNextDataStrategy,
)
from polars_baseball.parsers.mlb import MLBApiParser


@runtime_checkable
class Parser(Protocol):
    def parse(self, raw: str) -> pl.DataFrame: ...


__all__ = [
    # Legacy (kept for backward compatibility)
    "Parser",
    "BaseParser",
    "BRefGameLogParser",
    "MLBApiParser",
    # New extraction strategy types
    "BRefCSVExportStrategy",
    "BRefGameLogStrategy",
    "BRefStandardStrategy",
    "ChainResult",
    "ExtractionStrategy",
    "FangraphsNextDataStrategy",
    "ProbeResult",
    "ProviderChain",
    "StructureFingerprint",
]
