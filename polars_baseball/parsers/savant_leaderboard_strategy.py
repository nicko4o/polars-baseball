"""Savant extraction strategies for the ProviderChain degradation pattern.

Savant's leaderboard endpoints may return CSV or HTML depending on upstream
changes.  This module provides two ExtractionStrategy implementations:

  1. SavantCSVStrategy      — parses CSV responses (the happy path).
  2. SavantHTMLTableStrategy — parses HTML tables (fallback when CSV breaks).

Both implement the ExtractionStrategy Protocol from parsers._strategy.
"""

from __future__ import annotations

from typing import cast

import lxml.etree
import polars as pl
from lxml.etree import _Element

from polars_baseball.exceptions import UpstreamParseError
from polars_baseball.parsers._strategy import ProbeResult, StructureFingerprint
from polars_baseball.parsers.savant import SavantCSVParser

_CSV_INDICATORS = (",",)
_HTML_INDICATORS = ("<table",)
_SAVANT_INDICATORS = ("Statcast", "leaderboard")


class SavantCSVStrategy:
    """Extraction strategy for Savant CSV responses (happy path)."""

    def can_handle(self, raw: str) -> ProbeResult:
        stripped = raw.strip()
        if not stripped:
            return ProbeResult(can_handle=False, diagnostics="Empty content")

        if stripped.startswith("<"):
            return ProbeResult(can_handle=False, diagnostics="Content appears to be HTML, not CSV")

        if "," not in stripped:
            return ProbeResult(can_handle=False, diagnostics="No commas found; not CSV")

        return ProbeResult(can_handle=True, diagnostics="Content looks like valid CSV")

    def extract(self, raw: str) -> pl.DataFrame:
        return SavantCSVParser().parse(raw)

    def fingerprint(self) -> StructureFingerprint:
        return StructureFingerprint(source="Savant-CSV", required_indicators=_CSV_INDICATORS)


class SavantHTMLTableStrategy:
    """Fallback strategy that parses Savant HTML leaderboard tables with lxml."""

    def can_handle(self, raw: str) -> ProbeResult:
        stripped = raw.strip()
        if not stripped:
            return ProbeResult(can_handle=False, diagnostics="Empty content")

        has_table = any(ind in raw for ind in _HTML_INDICATORS)
        has_savant = any(ind in raw for ind in _SAVANT_INDICATORS)

        if has_table:
            diagnostics = "HTML table found" + (" (Savant indicators present)" if has_savant else "")
            return ProbeResult(can_handle=True, diagnostics=diagnostics)

        return ProbeResult(can_handle=False, diagnostics="No HTML table indicators found")

    def extract(self, raw: str) -> pl.DataFrame:
        try:
            tree = lxml.etree.HTML(raw)
            if tree is None:
                return pl.DataFrame()

            tables = cast(list[_Element], tree.xpath("//table"))
            if not tables:
                return pl.DataFrame()

            table = tables[0]

            th_elements = cast(list[_Element], table.xpath(".//thead//th | .//tr[1]//th"))
            if not th_elements:
                return pl.DataFrame()

            headers = [self._cell_text(th) for th in th_elements]

            tr_elements = cast(list[_Element], table.xpath(".//tbody//tr | .//tr"))
            if tr_elements and th_elements:
                tr_elements = tr_elements[1:] if len(tr_elements) > 1 else []

            rows: list[dict[str, str]] = []
            for tr in tr_elements:
                cells = cast(list[_Element], tr.xpath("./td"))
                if not cells:
                    continue
                row = {}
                for i, cell in enumerate(cells):
                    if i < len(headers):
                        row[headers[i]] = self._cell_text(cell)
                if row:
                    rows.append(row)

            return pl.DataFrame(rows)
        except Exception as exc:
            raise UpstreamParseError("Savant HTML leaderboard parsing failed.") from exc

    @staticmethod
    def _cell_text(cell: _Element) -> str:
        return "".join(str(x) for x in cell.itertext()).strip()

    def fingerprint(self) -> StructureFingerprint:
        return StructureFingerprint(source="Savant-HTML-Table", required_indicators=_HTML_INDICATORS)
