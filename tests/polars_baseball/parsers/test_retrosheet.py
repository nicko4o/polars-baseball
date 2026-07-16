import polars as pl
import pytest

from polars_baseball._schemas.retrosheet import GAMELOG_COLUMNS, ROSTER_COLUMNS, SCHEDULE_COLUMNS
from polars_baseball.exceptions import UpstreamParseError
from polars_baseball.parsers.retrosheet import (
    empty_rosters_frame,
    parse_gamelog_csv,
    parse_roster_csv,
    parse_schedule_csv,
    parse_season_contents,
)


def test_parse_season_contents_extracts_names() -> None:
    raw = b'[{"name":"GL2026.TXT"},{"name":"BOS2026.ROS"}]'

    assert parse_season_contents(raw, 2026) == ["GL2026.TXT", "BOS2026.ROS"]


def test_parse_season_contents_rejects_non_list() -> None:
    with pytest.raises(UpstreamParseError, match="Season 2026 not available"):
        parse_season_contents(b'{"name":"GL2026.TXT"}', 2026)


def test_parse_roster_csv_uses_roster_schema() -> None:
    df = parse_roster_csv(b"ohtans01,Ohtani,Shohei,L,R,LAA,DH\n")

    assert df.columns == list(ROSTER_COLUMNS)
    assert df["first_name"][0] == "Shohei"


def test_empty_rosters_frame_uses_roster_schema() -> None:
    df = empty_rosters_frame()

    assert isinstance(df, pl.DataFrame)
    assert df.is_empty()
    assert df.schema == {column: pl.String for column in ROSTER_COLUMNS}


def test_parse_schedule_csv_uses_schedule_schema() -> None:
    df = parse_schedule_csv(b"2026-04-01,0,Wed,NYA,AL,1,BOS,AL,1,D,,\n")

    assert df.columns == list(SCHEDULE_COLUMNS)
    assert df["visiting_team"][0] == "NYA"


def test_parse_gamelog_csv_uses_gamelog_schema() -> None:
    populated_values = ["20260401", "0", "Wed", "NYA", "AL", "1", "BOS", "AL", "1", "5", "4"]
    raw = ",".join([*populated_values, *([""] * (len(GAMELOG_COLUMNS) - len(populated_values)))]).encode()
    raw += b"\n"

    df = parse_gamelog_csv(raw)

    assert df.columns == list(GAMELOG_COLUMNS)
    assert df["visiting_score"][0] == 5
