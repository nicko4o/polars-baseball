import io
import zipfile
from pathlib import Path
from unittest.mock import AsyncMock

import polars as pl
import pytest

from polars_baseball._cache import FileCacheAdapter
from polars_baseball._client import HttpClient
from polars_baseball.client import BaseballClient


def create_mock_lahman_zip() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(
            "baseballdatabank-master/core/Parks.csv",
            "park_id,park_name\nBOS07,Fenway Park\n",
        )
        archive.writestr(
            "baseballdatabank-master/core/People.csv",
            "player_id,name_first\nohtan-sh01,Shohei\n",
        )
        archive.writestr(
            "baseballdatabank-master/contrib/Schools.csv",
            'school_id,school_name\n"HARVARD","Harvard University"\n',
        )
        archive.writestr(
            "baseballdatabank-master/core/Batting.csv",
            "player_id,year_id,g\nohtan-sh01,2026,150\n",
        )
    return buffer.getvalue()


@pytest.mark.asyncio
async def test_lahman_apis_use_compiled_table_cache(tmp_path: Path) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_bytes = AsyncMock(return_value=create_mock_lahman_zip())
    client = BaseballClient(http=mock_http, cache=FileCacheAdapter(tmp_path))

    df_parks = await client.lahman.parks()
    df_people = await client.lahman.people()
    df_schools = await client.lahman.schools()
    df_batting = await client.lahman.batting()

    assert isinstance(df_parks, pl.DataFrame)
    assert df_parks.height == 1
    assert df_parks["park_name"][0] == "Fenway Park"
    assert df_people["name_first"][0] == "Shohei"
    assert df_schools["school_name"][0] == "Harvard University"
    assert df_batting["g"][0] == 150
    assert (tmp_path / "compiled-datasets" / "lahman" / "core" / "Parks.parquet").exists()
    mock_http.get_bytes.assert_awaited_once()


@pytest.mark.asyncio
async def test_lahman_uses_injected_context_cache_dir(tmp_path: Path) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_bytes = AsyncMock(return_value=create_mock_lahman_zip())
    cache_dir = tmp_path / "context-cache"
    client = BaseballClient(http=mock_http, cache=FileCacheAdapter(cache_dir=cache_dir))

    df_parks = await client.lahman.parks()
    df_parks_again = await client.lahman.parks()

    assert df_parks.equals(df_parks_again)
    assert df_parks["park_name"][0] == "Fenway Park"
    assert (cache_dir / "compiled-datasets" / "lahman" / "core" / "Parks.parquet").exists()
    mock_http.get_bytes.assert_awaited_once()


@pytest.mark.asyncio
async def test_download_lahman_validates_archive_once(tmp_path: Path) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_bytes = AsyncMock(return_value=create_mock_lahman_zip())
    client = BaseballClient(http=mock_http, cache=FileCacheAdapter(cache_dir=tmp_path / "cache"))

    await client.lahman.download_lahman()

    assert (tmp_path / "cache" / "compiled-datasets" / "_archives" / "lahman.zip").exists()
    mock_http.get_bytes.assert_awaited_once()
