"""BRef extraction strategies wrapping existing BRefHTMLParser / BRefGameLogParser."""

from __future__ import annotations

import csv
import io
from typing import TYPE_CHECKING, cast

import lxml.etree
import polars as pl
from lxml.etree import ParserError, _Element

from polars_baseball.parsers._strategy import (
    ProbeResult,
    StructureFingerprint,
)

if TYPE_CHECKING:
    from polars_baseball.parsers.bref import BRefGameLogParser, BRefHTMLParser

_BREF_TABLE_INDICATORS = ("<table",)
_BREF_GAME_LOG_INDICATORS = ("<table", "players_standard_")
_CSV_EXPORT_INDICATORS = ("csv_", 'class="csv"')

__all__ = [
    "BRefCSVExportStrategy",
    "BRefGameLogStrategy",
    "BRefStandardStrategy",
]


class BRefStandardStrategy:
    """Wraps BRefHTMLParser as an ExtractionStrategy."""

    def __init__(self, parser: BRefHTMLParser) -> None:
        self._parser = parser

    def can_handle(self, raw: str) -> ProbeResult:
        has_table = "<table" in raw or "stats_table" in raw
        diagnostics = "BRef table indicators found" if has_table else "No BRef table found"
        return ProbeResult(can_handle=has_table, diagnostics=diagnostics)

    def extract(self, raw: str) -> pl.DataFrame:
        return self._parser.parse(raw)

    def fingerprint(self) -> StructureFingerprint:
        return StructureFingerprint(
            source="BRef-Standard-Table",
            required_indicators=_BREF_TABLE_INDICATORS,
        )


class BRefGameLogStrategy:
    """Wraps BRefGameLogParser as an ExtractionStrategy."""

    def __init__(self, parser: BRefGameLogParser) -> None:
        self._parser = parser

    def can_handle(self, raw: str) -> ProbeResult:
        has_gamelog = "players_standard_" in raw
        diagnostics = "BRef game log indicators found" if has_gamelog else "No BRef game log found"
        return ProbeResult(can_handle=has_gamelog, diagnostics=diagnostics)

    def extract(self, raw: str) -> pl.DataFrame:
        return self._parser.parse(raw)

    def fingerprint(self) -> StructureFingerprint:
        return StructureFingerprint(
            source="BRef-GameLog",
            required_indicators=_BREF_GAME_LOG_INDICATORS,
        )


class BRefCSVExportStrategy:
    """Fallback strategy extracting CSV data from BRef's embedded CSV export blocks.

    BRef embeds CSV data as hidden <table id="csv_..."> elements or
    <div class="csv"> blocks. This strategy extracts and parses them as
    raw CSV text, providing a parsing pathway independent of the display DOM.
    """

    def can_handle(self, raw: str) -> ProbeResult:
        for ind in _CSV_EXPORT_INDICATORS:
            if ind in raw:
                return ProbeResult(can_handle=True, diagnostics=f"BRef CSV indicator found: '{ind}'")
        return ProbeResult(can_handle=False, diagnostics="No BRef CSV export indicators found")

    def extract(self, raw: str) -> pl.DataFrame:
        try:
            tree = lxml.etree.HTML(raw)
            if tree is None:
                return pl.DataFrame()

            csv_tables = cast(list[_Element], tree.xpath("//table[starts-with(@id, 'csv_')]"))
            if csv_tables:
                return self._parse_csv_table(csv_tables[0])

            csv_divs = cast(list[_Element], tree.xpath("//div[@class='csv']"))
            if csv_divs:
                return self._parse_csv_div(csv_divs[0])

            return pl.DataFrame()
        except (ParserError, pl.exceptions.PolarsError):
            return pl.DataFrame()

    @staticmethod
    def _parse_csv_table(table: _Element) -> pl.DataFrame:
        """Parse a <table id="csv_..."> where each <tr> has <td> or <th> cells."""
        buf = io.StringIO()
        writer = csv.writer(buf)
        has_rows = False
        tr_elements = cast(list[_Element], table.xpath(".//tr"))
        for tr in tr_elements:
            cells = [
                "".join(str(x) for x in cell.itertext()).strip()
                for cell in cast(list[_Element], tr.xpath("./td | ./th"))
            ]
            if not cells:
                continue
            writer.writerow(cells)
            has_rows = True

        if not has_rows:
            return pl.DataFrame()

        buf.seek(0)
        return pl.read_csv(buf, null_values="NULL")

    @staticmethod
    def _parse_csv_div(div: _Element) -> pl.DataFrame:
        """Parse a <div class="csv"> containing plain CSV text."""
        text = "".join(str(x) for x in div.itertext()).strip()
        if not text:
            return pl.DataFrame()
        return pl.read_csv(io.StringIO(text), null_values="NULL")

    def fingerprint(self) -> StructureFingerprint:
        return StructureFingerprint(
            source="BRef-CSV-Export",
            required_indicators=_CSV_EXPORT_INDICATORS,
        )
