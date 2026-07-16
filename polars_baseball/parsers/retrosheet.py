import io
import json

import polars as pl

from polars_baseball._encoding import ensure_bytes
from polars_baseball._schemas.retrosheet import GAMELOG_COLUMNS, PARK_CODE_COLUMNS, ROSTER_COLUMNS, SCHEDULE_COLUMNS
from polars_baseball.exceptions import UpstreamParseError

EVENTS_SCHEMA: dict[str, pl.DataType | type[pl.DataType]] = {
    "season": pl.Int64,
    "event_type": pl.Utf8,
    "filename": pl.Utf8,
    "content": pl.Binary,
}


def event_content_row(season: int, event_type: str, filename: str, raw: str | bytes) -> dict[str, object]:
    return {
        "season": season,
        "event_type": event_type,
        "filename": filename,
        "content": ensure_bytes(raw),
    }


def events_frame(rows: list[dict[str, object]]) -> pl.DataFrame:
    return pl.DataFrame(rows, schema=EVENTS_SCHEMA)


def parse_season_contents(raw: str | bytes, season: int) -> list[str]:
    try:
        data = json.loads(raw)
        if not isinstance(data, list):
            raise UpstreamParseError(f"Season {season} not available")
        return [entry["name"] for entry in data]
    except (json.JSONDecodeError, KeyError, TypeError) as err:
        raise UpstreamParseError(f"Season {season} not available") from err


def parse_roster_csv(raw: str | bytes) -> pl.DataFrame:
    return pl.read_csv(
        io.BytesIO(ensure_bytes(raw)),
        has_header=False,
        new_columns=list(ROSTER_COLUMNS),
        quote_char='"',
    )


def empty_rosters_frame() -> pl.DataFrame:
    return pl.DataFrame(schema={column: pl.Utf8 for column in ROSTER_COLUMNS})


def parse_park_codes_csv(raw: str | bytes) -> pl.DataFrame:
    df = pl.read_csv(io.BytesIO(ensure_bytes(raw)))
    return df.rename(dict(zip(df.columns[: len(PARK_CODE_COLUMNS)], PARK_CODE_COLUMNS, strict=False)))


def parse_schedule_csv(raw: str | bytes) -> pl.DataFrame:
    return pl.read_csv(
        io.BytesIO(ensure_bytes(raw)),
        has_header=False,
        new_columns=list(SCHEDULE_COLUMNS),
        quote_char='"',
    )


def parse_gamelog_csv(raw: str | bytes) -> pl.DataFrame:
    return pl.read_csv(
        io.BytesIO(ensure_bytes(raw)),
        has_header=False,
        new_columns=list(GAMELOG_COLUMNS),
        quote_char='"',
        truncate_ragged_lines=True,
    )
