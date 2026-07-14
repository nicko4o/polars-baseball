import json
import re
from collections.abc import Mapping
from typing import cast

import polars as pl

from polars_baseball._json_utils import child_mapping
from polars_baseball._validation import validate_next_data_structure
from polars_baseball.exceptions import UpstreamStructureChangedError
from polars_baseball.parsers.base import BaseParser

_TARGET_QUERY_KEY = "leaders/major-league/data"
_NEXT_DATA_MISSING = "Failed to find __NEXT_DATA__ script block in FanGraphs HTML response."
_NEXT_DATA_INVALID = "Failed to decode __NEXT_DATA__ JSON from FanGraphs HTML response."
_TARGET_QUERY_MISSING = "Required FanGraphs leaders query key was not found in NEXT_DATA."
_PLAYER_DATA_MISSING = "FanGraphs leaders query was found but player data is empty or missing."
_PLAYER_DATA_INVALID = "FanGraphs leaders player data must be a list of JSON objects."

_NEXT_DATA_RE = re.compile(
    r'<script id="__NEXT_DATA__" type="application/json">(.*?)</script>',
    re.DOTALL,
)


class FangraphsHTMLParser(BaseParser):
    def parse(self, raw: str) -> pl.DataFrame:
        return self._parse_next_data(raw)

    @staticmethod
    def _clean_dataframe_html(df: pl.DataFrame) -> pl.DataFrame:
        utf8_cols = [
            pl.col(col).str.replace_all(r"<[^>]+>", "", literal=False).str.strip_chars().alias(col)
            for col in df.columns
            if df[col].dtype == pl.Utf8
        ]
        return df.with_columns(utf8_cols) if utf8_cols else df

    @staticmethod
    def _parse_next_data(html: str) -> pl.DataFrame:
        match = _NEXT_DATA_RE.search(html)
        if not match:
            raise UpstreamStructureChangedError(_NEXT_DATA_MISSING)

        try:
            data = json.loads(match.group(1))
        except json.JSONDecodeError as e:
            raise UpstreamStructureChangedError(_NEXT_DATA_INVALID) from e

        queries = validate_next_data_structure(data)

        for q in queries:
            if not FangraphsHTMLParser._is_target_query(q):
                continue

            player_data = FangraphsHTMLParser._extract_player_data(q)
            if not player_data:
                raise UpstreamStructureChangedError(_PLAYER_DATA_MISSING)

            df = pl.DataFrame(player_data, infer_schema_length=None)
            return FangraphsHTMLParser._clean_dataframe_html(df)

        raise UpstreamStructureChangedError(_TARGET_QUERY_MISSING)

    @staticmethod
    def _extract_player_data(query: Mapping[str, object]) -> list[Mapping[str, object]]:
        state = child_mapping(query, "state", "FanGraphs query state")
        data = child_mapping(state, "data", "FanGraphs query data")
        rows = data.get("data")
        if not isinstance(rows, list):
            raise UpstreamStructureChangedError(_PLAYER_DATA_MISSING)
        if not all(isinstance(row, Mapping) for row in rows):
            raise UpstreamStructureChangedError(_PLAYER_DATA_INVALID)
        return [cast(Mapping[str, object], row) for row in rows]

    @staticmethod
    def _is_target_query(query: Mapping[str, object]) -> bool:
        query_key = query.get("queryKey")
        return isinstance(query_key, list) and _TARGET_QUERY_KEY in query_key
