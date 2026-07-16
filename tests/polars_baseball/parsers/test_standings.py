import polars as pl
import pytest

from polars_baseball.exceptions import UpstreamParseError
from polars_baseball.parsers.standings import (
    STANDINGS_TYPES,
    _parse_division_records,
    _parse_team_record,
    parse_standings_payload,
)


def test_parse_team_record_basic() -> None:
    rec_tied = {
        "team": {"name": "Orioles"},
        "gamesBack": "-",
        "leagueRecord": {"wins": 101, "losses": 61, "pct": ".623"},
    }
    parsed_tied = _parse_team_record(rec_tied)
    assert parsed_tied["teamId"] is None
    assert parsed_tied["Tm"] == "Orioles"
    assert parsed_tied["W"] == 101
    assert parsed_tied["L"] == 61
    assert parsed_tied["W-L%"] == 0.623
    assert parsed_tied["GB"] is None

    rec_gb = {
        "team": {"name": "Red Sox"},
        "gamesBack": "1.5",
        "leagueRecord": {"wins": 90, "losses": 72, "pct": ".556"},
    }
    parsed_gb = _parse_team_record(rec_gb)
    assert parsed_gb["teamId"] is None
    assert parsed_gb["Tm"] == "Red Sox"
    assert parsed_gb["GB"] == 1.5

    rec_with_team_id = {
        "team": {"id": 110, "name": "Orioles"},
        "gamesBack": "-",
        "leagueRecord": {"wins": 101, "losses": 61, "pct": ".623"},
    }
    parsed_with_team_id = _parse_team_record(rec_with_team_id)
    assert parsed_with_team_id["teamId"] == 110


def test_parse_team_record_rejects_invalid_numeric_tokens() -> None:
    rec_bad_pct = {
        "team": {"name": "Orioles"},
        "gamesBack": "-",
        "leagueRecord": {"wins": 101, "losses": 61, "pct": "not-a-pct"},
    }
    with pytest.raises(UpstreamParseError, match="Invalid standings W-L% value"):
        _parse_team_record(rec_bad_pct)

    rec_bad_gb = {
        "team": {"name": "Red Sox"},
        "gamesBack": "not-games-back",
        "leagueRecord": {"wins": 78, "losses": 84, "pct": ".481"},
    }
    with pytest.raises(UpstreamParseError, match="Invalid standings GB value"):
        _parse_team_record(rec_bad_gb)


def test_parse_division_records_empty_payload_returns_schema() -> None:
    df = _parse_division_records({"division": {"id": 201, "name": "AL East"}}, season=2023)

    assert df.is_empty()
    assert df.schema == STANDINGS_TYPES


def test_parse_standings_payload_rejects_non_object_root() -> None:
    with pytest.raises(UpstreamParseError, match="Standings payload root must be object"):
        parse_standings_payload([], season=2023)


def test_parse_standings_payload_empty_records_returns_schema() -> None:
    df = parse_standings_payload({"records": []}, season=2023)

    assert isinstance(df, pl.DataFrame)
    assert df.is_empty()
    assert df.schema == STANDINGS_TYPES
