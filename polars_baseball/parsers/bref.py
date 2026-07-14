import io
from typing import cast

import lxml.etree
import polars as pl
from lxml.etree import _Element
from lxml.html import HtmlElement

from polars_baseball.exceptions import UpstreamParseError, UpstreamStructureChangedError
from polars_baseball.parsers.base import BaseParser
from polars_baseball.parsers.bref_schema import (
    sanitize_and_coerce_bref,
    sanitize_bref_nulls,
)

# Named constants for mlbID extraction — avoids magic strings in DOM traversal.
_MLB_ID_PARAM: str = "mlb_ID="
_MLBID_COLUMN: str = "mlbID"


class BRefHTMLParser(BaseParser):
    def parse(self, raw: str) -> pl.DataFrame:
        return self._to_dataframe(raw)

    @staticmethod
    def _parse_val(text: str | None) -> str | None:
        if text is None:
            return None
        text = text.strip()
        if text == "" or text.lower() in ("nan", "none", "null") or text in ("---", "---%"):
            return None
        return text

    @staticmethod
    def _clean_dataframe(df: pl.DataFrame) -> pl.DataFrame:
        return sanitize_and_coerce_bref(df)

    @staticmethod
    def _parse_table_elements(table_el: _Element) -> tuple[list[str], list[_Element]]:
        th_elements = cast(list[_Element], table_el.xpath(".//tr[1]//th"))
        headings = ["".join(str(x) for x in th.itertext()).strip() for th in th_elements]
        tr_elements = cast(list[_Element], table_el.xpath(".//tbody//tr"))
        if not tr_elements:
            tr_elements = cast(list[_Element], table_el.xpath(".//tr"))[1:]
        return headings, tr_elements

    @staticmethod
    def _extract_mlb_id(tr: _Element) -> str | None:
        """Extract the MLB player ID from an anchor href containing _MLB_ID_PARAM.

        The href format is: /players/...?mlb_ID=<numeric_id>
        Returns None when no matching anchor is found in the row.
        """
        for a in cast(list[_Element], tr.xpath(".//a")):
            href = a.get("href")
            if href and _MLB_ID_PARAM in href:
                return href.split(_MLB_ID_PARAM)[-1]
        return None

    @staticmethod
    def _to_dataframe(html: str) -> pl.DataFrame:
        try:
            tree = lxml.etree.HTML(html)
            if tree is None:
                return pl.DataFrame()

            tables = cast(list[_Element], tree.xpath("//table"))
            if not tables:
                return pl.DataFrame()
            table = tables[0]

            headings, tr_elements = BRefHTMLParser._parse_table_elements(table)
            drop_first = False
            if headings and headings[0] in ("", "#", "Rk"):
                drop_first = True
                headings = headings[1:]
            # Append the mlbID column using the named constant.
            headings.append(_MLBID_COLUMN)

            rows = []
            for tr in tr_elements:
                cell_elements = cast(list[_Element], tr.xpath("./th | ./td"))
                if not cell_elements:
                    continue

                cells = ["".join(str(x) for x in c.itertext()).strip() for c in cell_elements]

                if drop_first and cells:
                    cells = cells[1:]

                mlb_id = BRefHTMLParser._extract_mlb_id(tr)
                cells.append(mlb_id or "")

                row_data = {}
                for i, val in enumerate(cells):
                    if i < len(headings) and headings[i] != "":
                        row_data[headings[i]] = BRefHTMLParser._parse_val(val)
                rows.append(row_data)

            df = pl.DataFrame(rows)
            return BRefHTMLParser._clean_dataframe(df)
        except UpstreamParseError:
            raise
        except Exception as e:
            raise UpstreamStructureChangedError(f"Failed to parse Baseball Reference HTML table: {e}") from e


class BRefGameLogParser(BaseParser):
    _COLUMN_RENAMES = {
        "Gtm": "Game",
        "Unnamed: 3_level_1": "Home",
        "#": "NumPlayers",
        "Opp. Starter (GmeSc)": "OppStart",
        "Pitchers Used (Rest-GameScore-Dec)": "PitchersUsed",
    }

    def __init__(self, log_type: str) -> None:
        self.log_type = log_type

    @staticmethod
    def _text(node: _Element) -> str:
        return "".join(cast(list[str], node.xpath(".//text()"))).strip()

    def _parse_multi_level_headers(self, thead: _Element) -> list[list[str]]:
        header_rows = thead.findall(".//tr")
        parsed_headers: list[list[str]] = []
        for tr in header_rows:
            row_headers: list[str] = []
            th_list = cast(list[_Element], tr.xpath(".//th|.//td"))
            for cell in th_list:
                colspan = int(cell.get("colspan", "1"))
                row_headers.extend([self._text(cell)] * colspan)
            parsed_headers.append(row_headers)
        return parsed_headers

    def _flatten_headers(self, thead: _Element) -> list[str]:
        parsed_headers = self._parse_multi_level_headers(thead)
        if not parsed_headers:
            return []
        if len(parsed_headers) == 1:
            return [self._COLUMN_RENAMES.get(col, col) for col in parsed_headers[0]]

        max_len = max(len(header) for header in parsed_headers)
        aligned = [header + [""] * (max_len - len(header)) for header in parsed_headers]
        flat_cols: list[str] = []
        for level_0, level_1 in zip(aligned[0], aligned[1], strict=False):
            renamed = self._COLUMN_RENAMES.get(level_1, level_1)
            flat_cols.append(renamed if level_0 == "" or "Unnamed" in level_0 else f"{level_0}_{renamed}")
        return flat_cols

    def _extract_rows(self, table: _Element) -> list[list[str]]:
        tbody = table.find(".//tbody")
        tr_elements = tbody.findall(".//tr") if tbody is not None else table.findall(".//tr")
        rows: list[list[str]] = []
        for tr in tr_elements:
            if tr.get("class") == "thead":
                continue
            cells = [self._text(td) for td in cast(list[_Element], tr.xpath(".//td|.//th"))]
            if cells:
                rows.append(cells)
        return rows

    def _build_dataframe(self, rows: list[list[str]], flat_cols: list[str]) -> pl.DataFrame:
        if not rows:
            return pl.DataFrame(schema={col: pl.Utf8 for col in flat_cols})

        max_cols = len(flat_cols)
        col_data: dict[str, list[str]] = {col: [] for col in flat_cols}
        for row in rows:
            normalized = (row + [""] * max_cols)[:max_cols]
            for idx, value in enumerate(normalized):
                col_data[flat_cols[idx]].append(value)
        return pl.DataFrame(col_data)

    def _normalize_dataframe(self, df: pl.DataFrame) -> pl.DataFrame:
        from polars_baseball.parsers.bref_schema import (
            coerce_bref_schema,
        )

        df = sanitize_bref_nulls(df)
        if "Rk" in df.columns:
            df = df.drop("Rk")
        if df.height > 0:
            df = df.head(-1)
        if "Home" in df.columns:
            df = df.with_columns((pl.col("Home").is_null()).alias("Home"))
        if "Game" in df.columns:
            df = df.filter(pl.col("Game") != "Gtm")
        return coerce_bref_schema(df)

    def parse(self, raw: str) -> pl.DataFrame:
        parser = lxml.etree.HTMLParser()
        tree = lxml.etree.fromstring(raw.encode("utf-8"), parser)
        table_id = f"players_standard_{self.log_type}"
        tables = cast(list[_Element], tree.xpath(f"//table[@id='{table_id}']"))
        if not tables:
            raise UpstreamStructureChangedError(f"Table with id '{table_id}' not found on scraped page.")

        table = tables[0]
        thead = table.find(".//thead")
        if thead is None:
            raise UpstreamStructureChangedError("Table headers not found in the scraped page.")

        flat_cols = self._flatten_headers(thead)
        if not flat_cols:
            return pl.DataFrame()

        rows = self._extract_rows(table)
        return self._normalize_dataframe(self._build_dataframe(rows, flat_cols))


class BRefSplitsParser:
    def __init__(self, playerid: str, year: int | None, pitching: bool) -> None:
        self.playerid = playerid
        self.year = year
        self.pitching = pitching

    def get_player_info(self, html: str) -> dict[str, str]:
        # Return default empty structure if HTML content is empty.
        if not html.strip():
            return {"Position": "", "Bats": "", "Throws": ""}
        parser = lxml.etree.HTMLParser(remove_comments=False)
        tree = lxml.etree.parse(io.StringIO(html), parser)
        player_divs = cast(list[HtmlElement], tree.xpath("//div[@class='players']"))
        if not player_divs:
            return {"Position": "", "Bats": "", "Throws": ""}

        result: dict[str, str] = {"Position": "", "Bats": "", "Throws": ""}
        p_tags = cast(list[HtmlElement], player_divs[0].xpath(".//p"))
        for p in p_tags:
            text = "".join(cast(list[str], p.xpath(".//text()"))).strip()
            if text.startswith("Position:"):
                result["Position"] = text.replace("Position:", "").strip()
            if "Bats:" in text and "Throws:" in text:
                parts = text.split("\u2022")
                for part in parts:
                    if "Bats:" in part:
                        result["Bats"] = part.replace("Bats:", "").strip()
                    if "Throws:" in part:
                        result["Throws"] = part.replace("Throws:", "").strip()
        return result

    def _process_comment_container(
        self,
        container: HtmlElement,
        raw_data: list[list[str]],
        raw_level_data: list[list[str]],
    ) -> None:
        caption = cast(HtmlElement | None, container.find(".//caption"))
        split_type = caption.text.strip() if caption is not None and caption.text else ""

        target = raw_level_data if split_type.endswith("Level") else raw_data

        first_tr = cast(HtmlElement | None, container.find(".//tr"))
        if first_tr is None:
            return

        th_list = cast(list[HtmlElement], first_tr.xpath(".//th"))
        headings = ["".join(cast(list[str], th.xpath(".//text()"))).strip() for th in th_list]

        if self.year is None:
            headings = headings[1:]

        headings.extend(["Split Type", "Player ID"])

        if not target:
            target.append(headings)

        tr_elements = cast(list[HtmlElement], container.xpath(".//tr"))
        for tr in tr_elements[1:]:
            th_tag = cast(HtmlElement | None, tr.find(".//th"))
            if th_tag is not None:
                th_text = "".join(cast(list[str], th_tag.xpath(".//text()"))).strip()
                if th_text == "Split":
                    continue

            if self.year is None:
                cells = cast(list[HtmlElement], tr.xpath(".//td"))
            else:
                all_cells = cast(list[HtmlElement], tr.xpath(".//th | .//td"))
                cells = all_cells

            if not cells:
                continue

            cols_text = ["".join(cast(list[str], c.xpath(".//text()"))).strip() for c in cells]
            if split_type != "By Inning":
                cols_text.extend([split_type, self.playerid])
                target.append(cols_text)

    def _extract_split_tables(self, html: str) -> tuple[list[list[str]], list[list[str]]]:
        # Return empty lists if HTML content is empty to avoid lxml initialization error.
        if not html.strip():
            return [], []
        parser = lxml.etree.HTMLParser(remove_comments=False)
        tree = lxml.etree.parse(io.StringIO(html), parser)

        raw_data: list[list[str]] = []
        raw_level_data: list[list[str]] = []

        comments = cast(list[HtmlElement], tree.xpath("//comment()"))
        for comment in comments:
            comment_text = comment.text or ""
            inner = lxml.etree.HTML(comment_text)
            if inner is None:
                continue

            containers = cast(list[HtmlElement], inner.xpath("//div[@class='table_container']"))
            for container in containers:
                self._process_comment_container(container, raw_data, raw_level_data)

        return raw_data, raw_level_data

    def _process_splits_table(
        self,
        raw_rows: list[list[str]],
    ) -> pl.DataFrame:
        if not raw_rows:
            return pl.DataFrame()

        header = raw_rows[0]
        data_rows = raw_rows[1:]
        df = pl.DataFrame(data_rows, schema=[(c, pl.String) for c in header], orient="row")

        if "Player ID" in df.columns and "Split Type" in df.columns and "Split" in df.columns:
            df = df.filter((pl.col("Split") != "Split") & (pl.col("Player ID") == self.playerid))
            df = df.drop("Player ID")

        numeric_cols = [c for c in df.columns if c not in ("Split Type", "Split")]
        for col in numeric_cols:
            df = df.with_columns(pl.col(col).cast(pl.Float64, strict=False).alias(col))

        df = df.drop([c for c in df.columns if df[c].is_null().all()])

        if not self.pitching and all(c in df.columns for c in ("H", "2B", "3B", "HR")):
            df = df.with_columns((pl.col("H") - pl.col("2B") - pl.col("3B") - pl.col("HR")).alias("1B"))

        return df

    def parse(self, html: str) -> tuple[pl.DataFrame, dict[str, str], pl.DataFrame]:
        # Return empty dataframes and info if HTML content is empty.
        if not html.strip():
            return pl.DataFrame(), {"Position": "", "Bats": "", "Throws": ""}, pl.DataFrame()
        raw_data, raw_level_data = self._extract_split_tables(html)
        df_main = self._process_splits_table(raw_data)
        df_level = self._process_splits_table(raw_level_data) if self.pitching and raw_level_data else pl.DataFrame()
        info = self.get_player_info(html)
        return df_main, info, df_level
