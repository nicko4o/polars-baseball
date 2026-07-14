from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest

from polars_baseball.apis.mlb.team_lookup import resolve_team_id
from polars_baseball.exceptions import InvalidParameterError


@pytest.mark.asyncio
@patch("polars_baseball.apis.mlb.team_lookup.most_recent_season", return_value=2026)
@patch("polars_baseball.apis.mlb.team_lookup._fetch_mlb_teams")
async def test_resolve_team_id_matches_normalized_name(
    mock_fetch_mlb_teams: AsyncMock,
    mock_most_recent_season: MagicMock,
) -> None:
    mock_fetch_mlb_teams.return_value = pl.DataFrame(
        {
            "id": [147],
            "teamName": ["New York Yankees"],
        }
    )

    team_id = await resolve_team_id("new-york yankees")

    assert team_id == 147
    mock_fetch_mlb_teams.assert_awaited_once_with(season=2026, context=None)
    mock_most_recent_season.assert_called_once_with()


@pytest.mark.asyncio
@patch("polars_baseball.apis.mlb.team_lookup._fetch_mlb_teams")
async def test_resolve_team_id_rejects_unknown_team(mock_fetch_mlb_teams: AsyncMock) -> None:
    mock_fetch_mlb_teams.return_value = pl.DataFrame(
        {
            "id": [147],
            "teamName": ["Yankees"],
        }
    )

    with pytest.raises(InvalidParameterError, match="Could not resolve team name"):
        await resolve_team_id("Orioles")


@pytest.mark.asyncio
@patch("polars_baseball.apis.mlb.team_lookup._fetch_mlb_teams")
async def test_resolve_team_id_rejects_unknown_team_id(mock_fetch_mlb_teams: AsyncMock) -> None:
    mock_fetch_mlb_teams.return_value = pl.DataFrame(
        {
            "id": [-1],
            "teamName": ["Yankees"],
        }
    )

    with pytest.raises(InvalidParameterError, match="Could not resolve team name"):
        await resolve_team_id("Yankees")
