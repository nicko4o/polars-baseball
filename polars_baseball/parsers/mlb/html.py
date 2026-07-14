from typing import cast

import lxml.etree
import polars as pl

from polars_baseball.parsers.base import BaseParser


class MLBApiParser(BaseParser):
    """HTML table parser that returns all columns as pl.String.

    Type coercion is deliberately excluded here. The schema validation layer
    (validate_and_cast_schema) is the correct place to enforce column types,
    not the parser. Heuristic type inference (try int, then float) introduces
    silent data corruption risks and belongs to no layer at all.
    """

    @staticmethod
    def _node_text(node: lxml.etree._Element) -> str:
        return "".join(cast(list[str], node.xpath(".//text()"))).strip()

    def _table_headers(self, table: lxml.etree._Element) -> list[str]:
        thead = table.find(".//thead")
        if thead is not None:
            header_rows = thead.findall(".//tr")
            tr = header_rows[-1] if header_rows else None
        else:
            tr = table.find(".//tr")

        if tr is None:
            return []
        return [self._node_text(th) for th in cast(list[lxml.etree._Element], tr.xpath(".//th|.//td"))]

    def _table_rows(self, table: lxml.etree._Element) -> list[list[str]]:
        tbody = table.find(".//tbody")
        tr_elements = tbody.findall(".//tr") if tbody is not None else table.findall(".//tr")[1:]
        return [
            [self._node_text(td) for td in cast(list[lxml.etree._Element], tr.xpath(".//td|.//th"))]
            for tr in tr_elements
        ]

    @staticmethod
    def _normalize_rows(rows: list[list[str]], width: int) -> list[list[str | None]]:
        """Pad or truncate each row to the expected column width.

        Empty strings are converted to None to represent missing values.
        """
        normalized: list[list[str | None]] = []
        for row in rows:
            padded = row + [""] * max(0, width - len(row))
            normalized.append([value or None for value in padded[:width]])
        return normalized

    def _table_to_dataframe(self, table: lxml.etree._Element) -> pl.DataFrame:
        """Convert a single HTML table element to a string-typed DataFrame.

        All values are kept as pl.String. No heuristic type inference is performed.
        """
        headers = self._table_headers(table)
        rows = self._normalize_rows(self._table_rows(table), len(headers))
        if not headers or not rows:
            return pl.DataFrame()

        # Build column-oriented dict; all values remain as str | None.
        columns: dict[str, list[str | None]] = {
            header: [row[idx] for row in rows] for idx, header in enumerate(headers)
        }
        return pl.DataFrame(columns, schema={h: pl.String for h in headers})

    def parse_tables(self, raw: str) -> list[pl.DataFrame]:
        """Parse all non-empty HTML tables in the raw string."""
        parser = lxml.etree.HTMLParser()
        tree = lxml.etree.fromstring(raw.encode("utf-8"), parser)
        if tree is None:
            return []

        tables = cast(list[lxml.etree._Element], tree.xpath("//table"))
        return [df for table in tables if not (df := self._table_to_dataframe(table)).is_empty()]

    def parse(self, raw: str) -> pl.DataFrame:
        dfs = self.parse_tables(raw)
        if not dfs:
            return pl.DataFrame()
        return pl.concat(dfs, how="diagonal")
