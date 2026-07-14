from typing import Final

import polars as pl

from polars_baseball._config import LAHMAN_ARCHIVE_URL
from polars_baseball.context import BaseballContext, default_context
from polars_baseball.gateways.compiled import CompiledDatasetGateway, CompiledTable

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


def _resolve_context(context: BaseballContext | None) -> BaseballContext:
    return context or default_context()


def _lahman_table(filepath: str, quote_char: str) -> CompiledTable:
    return CompiledTable(
        dataset=LAHMAN_DATASET,
        table_name=filepath.removesuffix(".csv"),
        archive_url=LAHMAN_ARCHIVE_URL,
        archive_member=f"{LAHMAN_DIR_NAME}/{filepath}",
        quote_char=quote_char,
    )


async def download_lahman(context: BaseballContext | None = None) -> None:
    """Download the full Lahman baseball database archive if not already cached locally."""
    ctx = _resolve_context(context)
    await CompiledDatasetGateway(ctx).ensure_archive(LAHMAN_DATASET, LAHMAN_ARCHIVE_URL)


async def _get_lahman_file(
    filepath: str,
    quote_char: str = '"',
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    ctx = _resolve_context(context)
    table = _lahman_table(filepath, quote_char)
    return await CompiledDatasetGateway(ctx).read_table(table)


async def parks(context: BaseballContext | None = None) -> pl.DataFrame:
    """Fetch Lahman Parks table. Includes ballpark names, locations, and dimensions."""
    return await _get_lahman_file("core/Parks.csv", context=context)


async def all_star_full(context: BaseballContext | None = None) -> pl.DataFrame:
    """Fetch Lahman All-Star selections. Includes all players selected to All-Star games."""
    return await _get_lahman_file("core/AllstarFull.csv", context=context)


async def appearances(context: BaseballContext | None = None) -> pl.DataFrame:
    """Fetch Lahman Appearances table. Includes position and game appearance data per player per season."""
    return await _get_lahman_file("core/Appearances.csv", context=context)


async def awards_managers(context: BaseballContext | None = None) -> pl.DataFrame:
    """Fetch Lahman AwardsManagers table. Includes awards won by managers."""
    return await _get_lahman_file("contrib/AwardsManagers.csv", context=context)


async def awards_players(context: BaseballContext | None = None) -> pl.DataFrame:
    """Fetch Lahman AwardsPlayers table. Includes awards won by players."""
    return await _get_lahman_file("contrib/AwardsPlayers.csv", context=context)


async def awards_share_managers(context: BaseballContext | None = None) -> pl.DataFrame:
    """Fetch Lahman AwardsShareManagers table. Includes award voting results for managers."""
    return await _get_lahman_file("contrib/AwardsShareManagers.csv", context=context)


async def awards_share_players(context: BaseballContext | None = None) -> pl.DataFrame:
    """Fetch Lahman AwardsSharePlayers table. Includes award voting results for players."""
    return await _get_lahman_file("contrib/AwardsSharePlayers.csv", context=context)


async def batting(context: BaseballContext | None = None) -> pl.DataFrame:
    """Fetch Lahman Batting table. Includes season-level batting statistics for each player."""
    return await _get_lahman_file("core/Batting.csv", context=context)


async def batting_post(context: BaseballContext | None = None) -> pl.DataFrame:
    """Fetch Lahman BattingPost table. Includes postseason batting statistics for each player."""
    return await _get_lahman_file("core/BattingPost.csv", context=context)


async def college_playing(context: BaseballContext | None = None) -> pl.DataFrame:
    """Fetch Lahman CollegePlaying table. Includes college attendance records for players."""
    return await _get_lahman_file("contrib/CollegePlaying.csv", context=context)


async def fielding(context: BaseballContext | None = None) -> pl.DataFrame:
    """Fetch Lahman Fielding table. Includes season-level fielding statistics for each player."""
    return await _get_lahman_file("core/Fielding.csv", context=context)


async def fielding_of(context: BaseballContext | None = None) -> pl.DataFrame:
    """Fetch Lahman FieldingOF table. Includes outfield-specific fielding data."""
    return await _get_lahman_file("core/FieldingOF.csv", context=context)


async def fielding_of_split(context: BaseballContext | None = None) -> pl.DataFrame:
    """Fetch Lahman FieldingOFsplit table. Includes outfield fielding data split by position."""
    return await _get_lahman_file("core/FieldingOFsplit.csv", context=context)


async def fielding_post(context: BaseballContext | None = None) -> pl.DataFrame:
    """Fetch Lahman FieldingPost table. Includes postseason fielding statistics."""
    return await _get_lahman_file("core/FieldingPost.csv", context=context)


async def hall_of_fame(context: BaseballContext | None = None) -> pl.DataFrame:
    """Fetch Lahman HallOfFame table. Includes Hall of Fame voting results and inductees."""
    return await _get_lahman_file("contrib/HallOfFame.csv", context=context)


async def home_games(context: BaseballContext | None = None) -> pl.DataFrame:
    """Fetch Lahman HomeGames table. Includes home game location and attendance data per team per season."""
    return await _get_lahman_file("core/HomeGames.csv", context=context)


async def managers(context: BaseballContext | None = None) -> pl.DataFrame:
    """Fetch Lahman Managers table. Includes managerial records per team per season."""
    return await _get_lahman_file("core/Managers.csv", context=context)


async def managers_half(context: BaseballContext | None = None) -> pl.DataFrame:
    """Fetch Lahman ManagersHalf table. Includes split-season managerial records."""
    return await _get_lahman_file("core/ManagersHalf.csv", context=context)


async def people(context: BaseballContext | None = None) -> pl.DataFrame:
    """Fetch Lahman People table. Includes biographical data for all players."""
    return await _get_lahman_file("core/People.csv", context=context)


async def pitching(context: BaseballContext | None = None) -> pl.DataFrame:
    """Fetch Lahman Pitching table. Includes season-level pitching statistics for each player."""
    return await _get_lahman_file("core/Pitching.csv", context=context)


async def pitching_post(context: BaseballContext | None = None) -> pl.DataFrame:
    """Fetch Lahman PitchingPost table. Includes postseason pitching statistics."""
    return await _get_lahman_file("core/PitchingPost.csv", context=context)


async def salaries(context: BaseballContext | None = None) -> pl.DataFrame:
    """Fetch Lahman Salaries table. Includes player salary data per season."""
    return await _get_lahman_file("contrib/Salaries.csv", context=context)


async def schools(context: BaseballContext | None = None) -> pl.DataFrame:
    """Fetch Lahman Schools table. Includes school information for colleges in the database."""
    return await _get_lahman_file("contrib/Schools.csv", quote_char='"', context=context)


async def series_post(context: BaseballContext | None = None) -> pl.DataFrame:
    """Fetch Lahman SeriesPost table. Includes postseason series results."""
    return await _get_lahman_file("core/SeriesPost.csv", context=context)


async def teams_core(context: BaseballContext | None = None) -> pl.DataFrame:
    """Fetch Lahman Teams table. Includes season-level team statistics."""
    return await _get_lahman_file("core/Teams.csv", context=context)


async def teams_upstream(context: BaseballContext | None = None) -> pl.DataFrame:
    """Fetch Lahman upstream Teams table. An alternative version of the Teams table."""
    return await _get_lahman_file("upstream/Teams.csv", context=context)


async def teams_franchises(context: BaseballContext | None = None) -> pl.DataFrame:
    """Fetch Lahman TeamsFranchises table. Includes franchise-level metadata."""
    return await _get_lahman_file("core/TeamsFranchises.csv", context=context)


async def teams_half(context: BaseballContext | None = None) -> pl.DataFrame:
    """Fetch Lahman TeamsHalf table. Includes split-season team records."""
    return await _get_lahman_file("core/TeamsHalf.csv", context=context)
