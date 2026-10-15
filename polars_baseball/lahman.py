"""Namespaced client for Sean Lahman's Baseball Database endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING, Final

import polars as pl

from polars_baseball._config import LAHMAN_ARCHIVE_URL
from polars_baseball.gateways.compiled import CompiledDatasetGateway, CompiledTable

if TYPE_CHECKING:
    from polars_baseball.client import BaseballClient

LAHMAN_DATASET = "lahman"
LAHMAN_DIR_NAME = "baseballdatabank-master"
LAHMAN_TABLE_FILES: Final[tuple[str, ...]] = (
    "core/Parks.csv",
    "core/AllstarFull.csv",
    "core/Appearances.csv",
    "contrib/AwardsManagers.csv",
    "contrib/AwardsPlayers.csv",
    "contrib/AwardsShareManagers.csv",
    "contrib/AwardsSharePlayers.csv",
    "core/Batting.csv",
    "core/BattingPost.csv",
    "contrib/CollegePlaying.csv",
    "core/Fielding.csv",
    "core/FieldingOF.csv",
    "core/FieldingOFsplit.csv",
    "core/FieldingPost.csv",
    "contrib/HallOfFame.csv",
    "core/HomeGames.csv",
    "core/Managers.csv",
    "core/ManagersHalf.csv",
    "core/People.csv",
    "core/Pitching.csv",
    "core/PitchingPost.csv",
    "contrib/Salaries.csv",
    "contrib/Schools.csv",
    "core/SeriesPost.csv",
    "core/Teams.csv",
    "upstream/Teams.csv",
    "core/TeamsFranchises.csv",
    "core/TeamsHalf.csv",
)


def _lahman_table(filepath: str, quote_char: str) -> CompiledTable:
    return CompiledTable(
        dataset=LAHMAN_DATASET,
        table_name=filepath.removesuffix(".csv"),
        archive_url=LAHMAN_ARCHIVE_URL,
        archive_member=f"{LAHMAN_DIR_NAME}/{filepath}",
        quote_char=quote_char,
    )


class LahmanClient:
    """Namespaced Lahman database client."""

    def __init__(self, client: BaseballClient) -> None:
        self._client = client

    async def _get_lahman_file(self, filepath: str, quote_char: str = '"') -> pl.DataFrame:
        table = _lahman_table(filepath, quote_char)
        return await CompiledDatasetGateway(self._client).read_table(table)

    async def download_lahman(self) -> None:
        """Download the full Lahman baseball database archive if not already cached locally."""
        await CompiledDatasetGateway(self._client).ensure_archive(LAHMAN_DATASET, LAHMAN_ARCHIVE_URL)

    async def parks(self) -> pl.DataFrame:
        """Fetch Lahman Parks table. Includes ballpark names, locations, and dimensions."""
        return await self._get_lahman_file("core/Parks.csv")

    async def all_star_full(self) -> pl.DataFrame:
        """Fetch Lahman All-Star selections. Includes all players selected to All-Star games."""
        return await self._get_lahman_file("core/AllstarFull.csv")

    async def appearances(self) -> pl.DataFrame:
        """Fetch Lahman Appearances table. Includes position and game appearance data per player per season."""
        return await self._get_lahman_file("core/Appearances.csv")

    async def awards_managers(self) -> pl.DataFrame:
        """Fetch Lahman AwardsManagers table. Includes awards won by managers."""
        return await self._get_lahman_file("contrib/AwardsManagers.csv")

    async def awards_players(self) -> pl.DataFrame:
        """Fetch Lahman AwardsPlayers table. Includes awards won by players."""
        return await self._get_lahman_file("contrib/AwardsPlayers.csv")

    async def awards_share_managers(self) -> pl.DataFrame:
        """Fetch Lahman AwardsShareManagers table. Includes award voting results for managers."""
        return await self._get_lahman_file("contrib/AwardsShareManagers.csv")

    async def awards_share_players(self) -> pl.DataFrame:
        """Fetch Lahman AwardsSharePlayers table. Includes award voting results for players."""
        return await self._get_lahman_file("contrib/AwardsSharePlayers.csv")

    async def batting(self) -> pl.DataFrame:
        """Fetch Lahman Batting table. Includes season-level batting statistics for each player."""
        return await self._get_lahman_file("core/Batting.csv")

    async def batting_post(self) -> pl.DataFrame:
        """Fetch Lahman BattingPost table. Includes postseason batting statistics for each player."""
        return await self._get_lahman_file("core/BattingPost.csv")

    async def college_playing(self) -> pl.DataFrame:
        """Fetch Lahman CollegePlaying table. Includes college attendance records for players."""
        return await self._get_lahman_file("contrib/CollegePlaying.csv")

    async def fielding(self) -> pl.DataFrame:
        """Fetch Lahman Fielding table. Includes season-level fielding statistics for each player."""
        return await self._get_lahman_file("core/Fielding.csv")

    async def fielding_of(self) -> pl.DataFrame:
        """Fetch Lahman FieldingOF table. Includes outfield-specific fielding data."""
        return await self._get_lahman_file("core/FieldingOF.csv")

    async def fielding_of_split(self) -> pl.DataFrame:
        """Fetch Lahman FieldingOFsplit table. Includes outfield fielding data split by position."""
        return await self._get_lahman_file("core/FieldingOFsplit.csv")

    async def fielding_post(self) -> pl.DataFrame:
        """Fetch Lahman FieldingPost table. Includes postseason fielding statistics."""
        return await self._get_lahman_file("core/FieldingPost.csv")

    async def hall_of_fame(self) -> pl.DataFrame:
        """Fetch Lahman HallOfFame table. Includes Hall of Fame voting results and inductees."""
        return await self._get_lahman_file("contrib/HallOfFame.csv")

    async def home_games(self) -> pl.DataFrame:
        """Fetch Lahman HomeGames table. Includes home game location and attendance data per team per season."""
        return await self._get_lahman_file("core/HomeGames.csv")

    async def managers(self) -> pl.DataFrame:
        """Fetch Lahman Managers table. Includes managerial records per team per season."""
        return await self._get_lahman_file("core/Managers.csv")

    async def managers_half(self) -> pl.DataFrame:
        """Fetch Lahman ManagersHalf table. Includes split-season managerial records."""
        return await self._get_lahman_file("core/ManagersHalf.csv")

    async def people(self) -> pl.DataFrame:
        """Fetch Lahman People table. Includes biographical data for all players."""
        return await self._get_lahman_file("core/People.csv")

    async def pitching(self) -> pl.DataFrame:
        """Fetch Lahman Pitching table. Includes season-level pitching statistics for each player."""
        return await self._get_lahman_file("core/Pitching.csv")

    async def pitching_post(self) -> pl.DataFrame:
        """Fetch Lahman PitchingPost table. Includes postseason pitching statistics."""
        return await self._get_lahman_file("core/PitchingPost.csv")

    async def salaries(self) -> pl.DataFrame:
        """Fetch Lahman Salaries table. Includes player salary data per season."""
        return await self._get_lahman_file("contrib/Salaries.csv")

    async def schools(self) -> pl.DataFrame:
        """Fetch Lahman Schools table. Includes school information for colleges in the database."""
        return await self._get_lahman_file("contrib/Schools.csv", quote_char='"')

    async def series_post(self) -> pl.DataFrame:
        """Fetch Lahman SeriesPost table. Includes postseason series results."""
        return await self._get_lahman_file("core/SeriesPost.csv")

    async def teams_core(self) -> pl.DataFrame:
        """Fetch Lahman Teams table. Includes season-level team statistics."""
        return await self._get_lahman_file("core/Teams.csv")

    async def teams_upstream(self) -> pl.DataFrame:
        """Fetch Lahman upstream Teams table. An alternative version of the Teams table."""
        return await self._get_lahman_file("upstream/Teams.csv")

    async def teams_franchises(self) -> pl.DataFrame:
        """Fetch Lahman TeamsFranchises table. Includes franchise-level metadata."""
        return await self._get_lahman_file("core/TeamsFranchises.csv")

    async def teams_half(self) -> pl.DataFrame:
        """Fetch Lahman TeamsHalf table. Includes split-season team records."""
        return await self._get_lahman_file("core/TeamsHalf.csv")


def __getattr__(name: str) -> None:
    raise AttributeError(
        f"Top-level function 'polars_baseball.lahman.{name}' was removed. "
        f"Use BaseballClient: `client = BaseballClient(); await client.lahman.{name}(...)`."
    )


__all__ = ["LahmanClient"]
