"""Fangraphs extraction strategy wrapping existing FangraphsHTMLParser."""

from __future__ import annotations

from typing import TYPE_CHECKING

import polars as pl

from polars_baseball.parsers._strategy import (
    ProbeResult,
    StructureFingerprint,
)

if TYPE_CHECKING:
    from polars_baseball.parsers.fangraphs import FangraphsHTMLParser

_FANGRAPHS_INDICATORS = ("__NEXT_DATA__", "leaders/major-league/data")

__all__ = ["FangraphsNextDataStrategy"]


class FangraphsNextDataStrategy:
    """Wraps FangraphsHTMLParser as an ExtractionStrategy."""

    def __init__(self, parser: FangraphsHTMLParser | None = None) -> None:
        from polars_baseball.parsers.fangraphs import FangraphsHTMLParser

        self._parser = parser or FangraphsHTMLParser()

    def can_handle(self, raw: str) -> ProbeResult:
        missing = [ind for ind in _FANGRAPHS_INDICATORS if ind not in raw]
        if missing:
            return ProbeResult(can_handle=False, diagnostics=f"Missing Fangraphs indicators: {missing}")
        return ProbeResult(can_handle=True, diagnostics="Fangraphs NEXT_DATA structure detected")

    def extract(self, raw: str) -> pl.DataFrame:
        return self._parser.parse(raw)

    def fingerprint(self) -> StructureFingerprint:
        return StructureFingerprint(
            source="Fangraphs-NextData",
            required_indicators=_FANGRAPHS_INDICATORS,
        )
