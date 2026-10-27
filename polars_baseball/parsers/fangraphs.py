import json
import re
from collections.abc import Mapping
from typing import cast

import polars as pl

from polars_baseball._json_utils import child_mapping
from polars_baseball._schema_utils import validate_and_cast_schema
from polars_baseball._schemas.fangraphs import (
    FANGRAPHS_SCHEDULE_COLUMN_MAP,
    FANGRAPHS_SCHEDULE_REQUIRED,
    FANGRAPHS_SCHEDULE_TYPES,
)
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
    """Parse FanGraphs leaderboard HTML using __NEXT_DATA__ JSON embedded in the page.

    Extracts the <script id="__NEXT_DATA__"> block, decodes the
    leaders/major-league/data query key, and converts the player data
    array into a DataFrame. Strips HTML tags from string columns.
    """

    def parse(self, raw: str) -> pl.DataFrame:
        return self._parse_next_data(raw)

    @staticmethod
    def _clean_dataframe_html(df: pl.DataFrame) -> pl.DataFrame:
        utf8_cols = [
            pl.col(col).str.replace_all(r"<[^>]+>", "", literal=False).str.strip_chars().alias(col)
            for col in df.columns
            if df[col].dtype == pl.String
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
                return pl.DataFrame()

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


def parse_fangraphs_season_schedule(raw: str | bytes | Mapping[str, object]) -> pl.DataFrame:
    """Parse FanGraphs season schedule JSON into a DataFrame.

    Converts schedule items into a structured DataFrame with snake_case columns,
    normalizes -99.0 win probability values to null, and validates against
    FANGRAPHS_SCHEDULE_TYPES schema.
    """
    if isinstance(raw, (str, bytes)):
        try:
            data = json.loads(raw)
        except json.JSONDecodeError as e:
            raise UpstreamStructureChangedError("Failed to decode FanGraphs schedule JSON response.") from e
    elif isinstance(raw, Mapping):
        data = raw
    else:
        raise UpstreamStructureChangedError("FanGraphs schedule payload must be str, bytes, or mapping.")

    if not isinstance(data, Mapping):
        raise UpstreamStructureChangedError("FanGraphs schedule root payload must be a JSON object.")

    schedule_rows = data.get("schedule")
    if schedule_rows is None:
        raise UpstreamStructureChangedError("Missing 'schedule' key in FanGraphs schedule response.")
    if not isinstance(schedule_rows, list):
        raise UpstreamStructureChangedError("'schedule' in FanGraphs response must be a list.")

    if not schedule_rows:
        empty_data: dict[str, list[object]] = {col: [] for col in FANGRAPHS_SCHEDULE_TYPES}
        return pl.DataFrame(empty_data, schema=FANGRAPHS_SCHEDULE_TYPES)

    if not all(isinstance(r, Mapping) for r in schedule_rows):
        raise UpstreamStructureChangedError("Items in FanGraphs 'schedule' list must be JSON objects.")

    df = pl.DataFrame(schedule_rows, infer_schema_length=None)
    rename_map = {k: v for k, v in FANGRAPHS_SCHEDULE_COLUMN_MAP.items() if k in df.columns}
    df = df.rename(rename_map)

    # Coerce win probabilities: -99.0 indicates missing probability data -> convert to null
    for prob_col in ("team_win_prob", "home_win_prob"):
        if prob_col in df.columns:
            df = df.with_columns(
                pl.when(pl.col(prob_col).cast(pl.Float64, strict=False) == -99.0)
                .then(None)
                .otherwise(pl.col(prob_col).cast(pl.Float64, strict=False))
                .alias(prob_col)
            )

    return validate_and_cast_schema(df, FANGRAPHS_SCHEDULE_REQUIRED, FANGRAPHS_SCHEDULE_TYPES)
