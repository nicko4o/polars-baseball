import json
from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest

from polars_baseball._client import HttpClient
from polars_baseball.apis.standings import _parse_team_record, standings
from polars_baseball.context import BaseballContext
from polars_baseball.exceptions import InvalidParameterError, UpstreamParseError

# ── Mock Data ──────────────────────────────────────────────────────────

_MOCK_STANDINGS_JSON = {
    "records": [
        {
            "standingsType": "regularSeason",
            "division": {"id": 201, "name": "American League East"},
            "teamRecords": [
                {
                    "team": {"id": 110, "name": "Orioles"},
                    "season": "2023",
                    "gamesPlayed": 162,
                    "gamesBack": "-",
                    "leagueRecord": {"wins": 101, "losses": 61, "pct": ".623"},
                },
                {
                    "team": {"id": 111, "name": "Red Sox"},
                    "season": "2023",
                    "gamesPlayed": 162,
                    "gamesBack": "12.5",
                    "leagueRecord": {"wins": 78, "losses": 84, "pct": ".481"},
                },
            ],
        },
        {
            "standingsType": "regularSeason",
            "division": {"id": 202, "name": "American League Central"},
            "teamRecords": [
                {
                    "team": {"id": 145, "name": "White Sox"},
                    "season": "2023",
                    "gamesPlayed": 162,
                    "gamesBack": "40.0",
                    "leagueRecord": {"wins": 61, "losses": 101, "pct": ".377"},
                },
            ],
        },
    ]
}


# ── Unit Tests ─────────────────────────────────────────────────────────


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


@pytest.mark.asyncio
@patch("polars_baseball.apis.standings.default_context")
async def test_standings_modern(mock_default_ctx: MagicMock) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=json.dumps(_MOCK_STANDINGS_JSON))
    mock_default_ctx.return_value = BaseballContext(http=mock_http)

    df = await standings(season=2023)
    assert isinstance(df, pl.DataFrame)
    assert df.height == 3
    assert df["season"][0] == 2023
    assert df["division_id"][0] == 201
    assert df["division_name"][0] == "American League East"
    assert df["teamId"][0] == 110
    assert df["Tm"][0] == "Orioles"
    assert df["W"][0] == 101
    assert df["L"][0] == 61
    assert df["W-L%"][0] == 0.623
    assert df["GB"][0] is None
    assert df["teamId"][1] == 111
    assert df["Tm"][1] == "Red Sox"
    assert df["W"][1] == 78
    assert df["L"][1] == 84
    assert df["W-L%"][1] == 0.481
    assert df["GB"][1] == 12.5
    assert df["division_id"][2] == 202
    assert df["division_name"][2] == "American League Central"


@pytest.mark.asyncio
async def test_standings_too_early() -> None:
    with pytest.raises(InvalidParameterError) as exc_info:
        await standings(season=1875)
    assert "1876" in str(exc_info.value)


@pytest.mark.asyncio
@patch("polars_baseball.apis.standings.default_context")
async def test_standings_upstream_failure(mock_default_ctx: MagicMock) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(side_effect=Exception("Timeout"))
    mock_default_ctx.return_value = BaseballContext(http=mock_http)
    with pytest.raises(UpstreamParseError, match="Failed to fetch or parse standings"):
        await standings(season=2023)
