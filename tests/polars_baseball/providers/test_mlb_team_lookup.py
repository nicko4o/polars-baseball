from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest

from polars_baseball.client import BaseballClient
from polars_baseball.exceptions import InvalidParameterError


@pytest.mark.asyncio
@patch("polars_baseball._mlb._taxonomy.most_recent_season", return_value=2026)
async def test_resolve_team_id_matches_normalized_name(
    mock_most_recent_season: MagicMock,
) -> None:
    client = BaseballClient()
    client.mlb.teams = AsyncMock(  # type: ignore[method-assign]
        return_value=pl.DataFrame(
            {
                "id": [147],
                "teamName": ["New York Yankees"],
            }
        )
    )

    team_id = await client.mlb.resolve_team_id("new-york yankees")

    assert team_id == 147
    client.mlb.teams.assert_awaited_once_with(season=2026)
    mock_most_recent_season.assert_called_once_with()


@pytest.mark.asyncio
async def test_resolve_team_id_rejects_unknown_team() -> None:
    client = BaseballClient()
    client.mlb.teams = AsyncMock(  # type: ignore[method-assign]
        return_value=pl.DataFrame(
            {
                "id": [147],
                "teamName": ["Yankees"],
            }
        )
    )

    with pytest.raises(InvalidParameterError, match="Could not resolve team name"):
        await client.mlb.resolve_team_id("Orioles")


@pytest.mark.asyncio
async def test_resolve_team_id_rejects_unknown_team_id() -> None:
    client = BaseballClient()
    client.mlb.teams = AsyncMock(  # type: ignore[method-assign]
        return_value=pl.DataFrame(
            {
                "id": [-1],
                "teamName": ["Yankees"],
            }
        )
    )

    with pytest.raises(InvalidParameterError, match="Could not resolve team name"):
        await client.mlb.resolve_team_id("Yankees")
