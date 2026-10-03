from typing import TYPE_CHECKING, cast

import polars as pl

from polars_baseball._config import DEFAULT_CSV_INFER_SCHEMA_LENGTH
from polars_baseball.parsers.base import BaseParser
from polars_baseball.parsers.savant_schema import SAVANT_SCHEMA_OVERRIDES

if TYPE_CHECKING:
    from lxml.etree import _Element


class SavantCSVParser(BaseParser):
    def parse(self, raw: str | bytes) -> pl.DataFrame:
        return self._to_dataframe(raw)

    @staticmethod
    def _to_dataframe(csv_data: str | bytes) -> pl.DataFrame:
        if not csv_data.strip():
            return pl.DataFrame()

        raw_bytes = csv_data if isinstance(csv_data, bytes) else csv_data.encode("utf-8")
        df = pl.read_csv(
            raw_bytes,
            infer_schema_length=DEFAULT_CSV_INFER_SCHEMA_LENGTH,
            null_values=[""],
        )

        df = df.rename({col: col.strip() for col in df.columns})

        string_cols = [col for col, dtype in df.schema.items() if dtype == pl.String]
        if string_cols:
            df = df.with_columns(pl.col(c).str.strip_chars().alias(c) for c in string_cols)

        active_casts = {k: v for k, v in SAVANT_SCHEMA_OVERRIDES.items() if k in df.columns}
        if active_casts:
            df = df.with_columns(pl.col(k).cast(v, strict=False).alias(k) for k, v in active_casts.items())

        return df


def _check_savant_error_row(raw_text: str) -> None:
    stripped = raw_text.strip()
    if not (stripped.startswith("error\n") or stripped.startswith("error,") or "error" in stripped[:200].lower()):
        return

    from polars_baseball.exceptions import UpstreamParseError

    try:
        df_err = pl.read_csv(raw_text.encode("utf-8"))
        if "error" in df_err.columns and df_err.height > 0:
            raise UpstreamParseError(str(df_err["error"][0]))
        if "error" in df_err.columns:
            raise UpstreamParseError("Savant request failed with an error row.")
    except pl.exceptions.PolarsError:
        if "error" in stripped[:200]:
            raise UpstreamParseError("Savant request failed with an error row.") from None


def _parse_savant_embedded_json(raw_text: str) -> pl.DataFrame:
    import json
    import re

    from polars_baseball.exceptions import UpstreamParseError, UpstreamStructureChangedError

    match = re.search(r"var data = (\[.*?\]);", raw_text, re.DOTALL)
    if not match:
        raise UpstreamStructureChangedError("Could not extract 'var data = [...]' JSON payload.")
    try:
        rows = json.loads(match.group(1))
        if not isinstance(rows, list):
            raise UpstreamStructureChangedError("Embedded JSON payload is not a list.")
        return pl.DataFrame(rows)
    except json.JSONDecodeError as exc:
        raise UpstreamParseError("Savant embedded JSON is not valid JSON.") from exc


def _parse_savant_html_table(raw_text: str) -> pl.DataFrame:
    import lxml.etree

    from polars_baseball.exceptions import UpstreamParseError, UpstreamStructureChangedError

    try:
        tree = lxml.etree.HTML(raw_text)
        if tree is None:
            raise UpstreamStructureChangedError("Savant HTML response has no document tree.")

        tables = cast(list["_Element"], tree.xpath("//table"))
        if not tables:
            raise UpstreamStructureChangedError("Savant HTML response has no table.")

        table = tables[0]
        th_elements = cast(list["_Element"], table.xpath(".//thead//th | .//tr[1]//th"))
        if not th_elements:
            raise UpstreamStructureChangedError("Savant HTML leaderboard table has no headers.")

        headers = ["".join(str(x) for x in th.itertext()).strip() for th in th_elements]

        tr_elements = cast(list["_Element"], table.xpath(".//tbody//tr | .//tr"))
        if tr_elements and th_elements:
            tr_elements = tr_elements[1:] if len(tr_elements) > 1 else []

        rows_data: list[dict[str, str]] = []
        for tr in tr_elements:
            cells = cast(list["_Element"], tr.xpath("./td"))
            if not cells:
                continue
            row = {
                headers[i]: "".join(str(x) for x in cell.itertext()).strip()
                for i, cell in enumerate(cells)
                if i < len(headers)
            }
            if row:
                rows_data.append(row)

        return pl.DataFrame(rows_data)
    except UpstreamStructureChangedError:
        raise
    except Exception as exc:
        raise UpstreamParseError("Savant HTML leaderboard parsing failed.") from exc


def parse_savant_leaderboard(raw: str | bytes) -> pl.DataFrame:
    """Parse Savant leaderboard content trying CSV first, then embedded JSON, then HTML table.

    Fails fast with UpstreamStructureChangedError if none of the formats match,
    or UpstreamParseError if error responses or corrupted formats are encountered.
    """
    from polars_baseball._encoding import ensure_str
    from polars_baseball.exceptions import UpstreamStructureChangedError

    raw_text = ensure_str(raw)
    stripped = raw_text.strip()
    if not stripped:
        return pl.DataFrame()

    _check_savant_error_row(raw_text)

    if not stripped.startswith("<") and "," in stripped:
        return SavantCSVParser().parse(raw_text)

    if "var data =" in stripped:
        return _parse_savant_embedded_json(raw_text)

    if "<table" in stripped:
        return _parse_savant_html_table(raw_text)

    raise UpstreamStructureChangedError(
        "Savant response does not match any recognized format (CSV, embedded JSON, or HTML table)."
    )


def parse_savant_park_factors(df: pl.DataFrame) -> pl.DataFrame:
    """Parse and normalize Savant Statcast Park Factors dataset."""
    from polars_baseball._schema_utils import validate_and_cast_schema
    from polars_baseball._schemas.savant import SAVANT_PARK_FACTORS_REQUIRED, SAVANT_PARK_FACTORS_TYPES

    if df.is_empty():
        return pl.DataFrame()

    column_mapping = {
        "venue_id": "venue_id",
        "venue_name": "venue_name",
        "main_team_id": "team_id",
        "name_display_club": "team_name",
        "key_year": "year",
        "year_range": "year_range",
        "key_bat_side": "bat_side",
        "n_pa": "n_pa",
        "index_woba": "park_factor",
        "index_runs": "runs_factor",
        "index_hr": "hr_factor",
        "index_hits": "hits_factor",
        "index_1b": "singles_factor",
        "index_2b": "doubles_factor",
        "index_3b": "triples_factor",
        "index_so": "so_factor",
        "index_bb": "bb_factor",
        "index_hardhit": "hard_hit_factor",
    }

    existing_renames = {k: v for k, v in column_mapping.items() if k in df.columns}
    df = df.rename(existing_renames)

    if "park_factor" in df.columns and "woba_factor" not in df.columns:
        df = df.with_columns(pl.col("park_factor").alias("woba_factor"))

    df = validate_and_cast_schema(df, SAVANT_PARK_FACTORS_REQUIRED, SAVANT_PARK_FACTORS_TYPES)
    return df.filter(pl.col("venue_id").is_not_null() & (pl.col("venue_id") > 0))
