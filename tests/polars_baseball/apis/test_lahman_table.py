from pathlib import Path
from unittest.mock import AsyncMock

import polars as pl
import pytest

from polars_baseball._cache import FileCacheAdapter
from polars_baseball._client import HttpClient
from polars_baseball.apis import lahman as L
from polars_baseball.context import BaseballContext

LAHMAN_CSV = "id,name\n1,test\n"

UNCOVERED_FUNCTIONS: list[tuple[str, str]] = [
    ("all_star_full", "core/AllstarFull.csv"),
    ("appearances", "core/Appearances.csv"),
    ("awards_managers", "contrib/AwardsManagers.csv"),
    ("awards_players", "contrib/AwardsPlayers.csv"),
    ("awards_share_managers", "contrib/AwardsShareManagers.csv"),
    ("awards_share_players", "contrib/AwardsSharePlayers.csv"),
    ("batting_post", "core/BattingPost.csv"),
    ("college_playing", "contrib/CollegePlaying.csv"),
    ("fielding", "core/Fielding.csv"),
    ("fielding_of", "core/FieldingOF.csv"),
    ("fielding_of_split", "core/FieldingOFsplit.csv"),
    ("fielding_post", "core/FieldingPost.csv"),
    ("hall_of_fame", "contrib/HallOfFame.csv"),
    ("home_games", "core/HomeGames.csv"),
    ("managers", "core/Managers.csv"),
    ("managers_half", "core/ManagersHalf.csv"),
    ("pitching", "core/Pitching.csv"),
    ("pitching_post", "core/PitchingPost.csv"),
    ("salaries", "contrib/Salaries.csv"),
    ("series_post", "core/SeriesPost.csv"),
    ("teams_core", "core/Teams.csv"),
    ("teams_upstream", "upstream/Teams.csv"),
    ("teams_franchises", "core/TeamsFranchises.csv"),
    ("teams_half", "core/TeamsHalf.csv"),
]

ALREADY_COVERED = {"parks", "people", "schools", "batting"}  # in existing test_lahman.py

ALL_FUNCTIONS = [(name, path) for name, path in UNCOVERED_FUNCTIONS if name not in ALREADY_COVERED]


def _build_lahman_zip() -> bytes:
    import io
    import zipfile

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("baseballdatabank-master/core/AllstarFull.csv", LAHMAN_CSV)
        archive.writestr("baseballdatabank-master/core/Appearances.csv", LAHMAN_CSV)
        archive.writestr("baseballdatabank-master/contrib/AwardsManagers.csv", LAHMAN_CSV)
        archive.writestr("baseballdatabank-master/contrib/AwardsPlayers.csv", LAHMAN_CSV)
        archive.writestr("baseballdatabank-master/contrib/AwardsShareManagers.csv", LAHMAN_CSV)
        archive.writestr("baseballdatabank-master/contrib/AwardsSharePlayers.csv", LAHMAN_CSV)
        archive.writestr("baseballdatabank-master/core/BattingPost.csv", LAHMAN_CSV)
        archive.writestr("baseballdatabank-master/contrib/CollegePlaying.csv", LAHMAN_CSV)
        archive.writestr("baseballdatabank-master/core/Fielding.csv", LAHMAN_CSV)
        archive.writestr("baseballdatabank-master/core/FieldingOF.csv", LAHMAN_CSV)
        archive.writestr("baseballdatabank-master/core/FieldingOFsplit.csv", LAHMAN_CSV)
        archive.writestr("baseballdatabank-master/core/FieldingPost.csv", LAHMAN_CSV)
        archive.writestr("baseballdatabank-master/contrib/HallOfFame.csv", LAHMAN_CSV)
        archive.writestr("baseballdatabank-master/core/HomeGames.csv", LAHMAN_CSV)
        archive.writestr("baseballdatabank-master/core/Managers.csv", LAHMAN_CSV)
        archive.writestr("baseballdatabank-master/core/ManagersHalf.csv", LAHMAN_CSV)
        archive.writestr("baseballdatabank-master/core/Pitching.csv", LAHMAN_CSV)
        archive.writestr("baseballdatabank-master/core/PitchingPost.csv", LAHMAN_CSV)
        archive.writestr("baseballdatabank-master/contrib/Salaries.csv", LAHMAN_CSV)
        archive.writestr("baseballdatabank-master/core/SeriesPost.csv", LAHMAN_CSV)
        archive.writestr("baseballdatabank-master/core/Teams.csv", LAHMAN_CSV)
        archive.writestr("baseballdatabank-master/upstream/Teams.csv", LAHMAN_CSV)
        archive.writestr("baseballdatabank-master/core/TeamsFranchises.csv", LAHMAN_CSV)
        archive.writestr("baseballdatabank-master/core/TeamsHalf.csv", LAHMAN_CSV)
    return buffer.getvalue()


@pytest.mark.asyncio
async def test_download_lahman_archive_exists(tmp_path: Path) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    data = _build_lahman_zip()
    mock_http.get_bytes = AsyncMock(return_value=data)
    ctx = BaseballContext(http=mock_http, cache=FileCacheAdapter(tmp_path / "cache"))

    await L.download_lahman(context=ctx)

    assert (tmp_path / "cache" / "compiled-datasets" / "_archives" / "lahman.zip").exists()
    mock_http.get_bytes.assert_awaited_once()


@pytest.mark.asyncio
@pytest.mark.parametrize("func_name,filepath", ALL_FUNCTIONS)
async def test_lahman_uncovered_functions(tmp_path: Path, func_name: str, filepath: str) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_bytes = AsyncMock(return_value=_build_lahman_zip())
    ctx = BaseballContext(http=mock_http, cache=FileCacheAdapter(tmp_path / "cache"))

    func = getattr(L, func_name)
    df = await func(context=ctx)

    assert isinstance(df, pl.DataFrame)
    assert df.height == 1
    assert df["name"][0] == "test"

    expected_parquet = tmp_path / "cache" / "compiled-datasets" / "lahman" / filepath
    assert expected_parquet.with_suffix(".parquet").exists()
    mock_http.get_bytes.assert_awaited_once()
