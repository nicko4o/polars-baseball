import asyncio
import io
import zipfile
from pathlib import Path
from typing import cast
from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest

from polars_baseball._cache import FileCacheAdapter, NullCacheAdapter
from polars_baseball.apis.playerid import (
    chadwick_register,
    player_name_suggestions,
    player_search_list,
    playerid_lookup,
    playerid_reverse_lookup,
)
from polars_baseball.context import BaseballContext
from polars_baseball.enums.player import KeyType
from polars_baseball.exceptions import InvalidParameterError, UpstreamParseError


def _register_zip(csv_text: str, filename: str = "register-master/data/people.csv") -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(filename, csv_text)
    return buffer.getvalue()


_REGISTER_CSV = (
    "name_last,name_first,key_mlbam,key_retro,key_bbref,key_fangraphs,mlb_played_first,mlb_played_last\n"
    "trout,mike,545361,troum001,troutmi01,10155,2011,2026\n"
)


@pytest.fixture
def mock_player_table() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "name_last": ["trout", "judge", "valenzuela"],
            "name_first": ["mike", "aaron", "fernando"],
            "key_mlbam": [545361, 592450, 123617],
            "key_retro": ["troum001", "judga001", "valef001"],
            "key_bbref": ["troutmi01", "judgeaa01", "valenfe01"],
            "key_fangraphs": [10155, 15640, 1011],
            "mlb_played_first": [2011, 2016, 1980],
            "mlb_played_last": [2026, 2026, 1997],
        }
    )


@pytest.mark.asyncio
async def test_chadwick_register_uses_injected_context_cache(tmp_path: Path) -> None:
    mock_http = MagicMock()
    mock_http.get_bytes = AsyncMock(return_value=_register_zip(_REGISTER_CSV))
    ctx = BaseballContext(http=mock_http, cache=FileCacheAdapter(tmp_path))

    first = await chadwick_register(context=ctx)
    second = await chadwick_register(context=ctx)

    assert first.equals(second)
    assert mock_http.get_bytes.await_count == 1


@pytest.mark.asyncio
async def test_chadwick_register_coalesces_concurrent_cache_misses(tmp_path: Path) -> None:
    async def get_bytes(url: str) -> bytes:
        await asyncio.sleep(0)
        return _register_zip(_REGISTER_CSV)

    mock_http = MagicMock()
    mock_http.get_bytes = AsyncMock(side_effect=get_bytes)
    ctx = BaseballContext(http=mock_http, cache=FileCacheAdapter(tmp_path))

    results = await asyncio.gather(
        chadwick_register(context=ctx),
        chadwick_register(context=ctx),
        chadwick_register(context=ctx),
    )

    assert mock_http.get_bytes.await_count == 1
    assert all(result.equals(results[0]) for result in results)


@pytest.mark.asyncio
async def test_chadwick_register_save_false_skips_cache(tmp_path: Path) -> None:
    mock_http = MagicMock()
    mock_http.get_bytes = AsyncMock(return_value=_register_zip(_REGISTER_CSV))
    ctx = BaseballContext(http=mock_http, cache=FileCacheAdapter(tmp_path))

    await chadwick_register(save=False, context=ctx)
    await chadwick_register(save=False, context=ctx)

    assert mock_http.get_bytes.await_count == 2
    assert not list(tmp_path.glob("*.parquet"))


@pytest.mark.asyncio
async def test_chadwick_register_null_cache_fetches_without_file_cache() -> None:
    mock_http = MagicMock()
    mock_http.get_bytes = AsyncMock(return_value=_register_zip(_REGISTER_CSV))
    ctx = BaseballContext(http=mock_http, cache=NullCacheAdapter())

    first = await chadwick_register(context=ctx)
    second = await chadwick_register(context=ctx)

    assert first.equals(second)
    assert mock_http.get_bytes.await_count == 2


@pytest.mark.asyncio
async def test_chadwick_register_fails_when_archive_has_no_people_csv(tmp_path: Path) -> None:
    mock_http = MagicMock()
    mock_http.get_bytes = AsyncMock(return_value=_register_zip("unused\n", filename="register-master/README.md"))
    ctx = BaseballContext(http=mock_http, cache=FileCacheAdapter(tmp_path))

    with pytest.raises(UpstreamParseError, match="people"):
        await chadwick_register(context=ctx)


@pytest.mark.asyncio
@patch("polars_baseball.apis.playerid.get_lookup_table")
async def test_playerid_lookup_exact(mock_get_table: MagicMock, mock_player_table: pl.DataFrame) -> None:
    mock_get_table.return_value = mock_player_table

    df = await playerid_lookup(last="Trout", first="Mike")
    assert isinstance(df, pl.DataFrame)
    assert df.height == 1
    assert df["key_mlbam"][0] == 545361

    df_judge = await playerid_lookup(last="Judge")
    assert df_judge.height == 1
    assert df_judge["key_mlbam"][0] == 592450


@pytest.mark.asyncio
@patch("polars_baseball.apis.playerid.get_lookup_table")
async def test_playerid_lookup_fuzzy(mock_get_table: MagicMock, mock_player_table: pl.DataFrame) -> None:
    mock_get_table.return_value = mock_player_table

    df = await playerid_lookup(last="Trut", first="Mike", fuzzy=True)
    assert df.is_empty()


@pytest.mark.asyncio
@patch("polars_baseball.apis.playerid.get_lookup_table")
async def test_player_name_suggestions_returns_fuzzy_matches(
    mock_get_table: MagicMock, mock_player_table: pl.DataFrame
) -> None:
    mock_get_table.return_value = mock_player_table

    df = await player_name_suggestions(last="Trut", first="Mike")

    assert df.height == 3
    assert 545361 in df["key_mlbam"].to_list()


@pytest.mark.asyncio
@patch("polars_baseball.apis.playerid.get_lookup_table")
async def test_playerid_lookup_accents(mock_get_table: MagicMock, mock_player_table: pl.DataFrame) -> None:
    mock_get_table.return_value = mock_player_table

    df = await playerid_lookup(last="Valenzuéla", first="Fernando", ignore_accents=True)
    assert df.height == 1
    assert df["key_mlbam"][0] == 123617


@pytest.mark.asyncio
@patch("polars_baseball.apis.playerid.get_lookup_table")
async def test_player_search_list(mock_get_table: MagicMock, mock_player_table: pl.DataFrame) -> None:
    mock_get_table.return_value = mock_player_table

    df = await player_search_list([("Trout", "Mike"), ("Judge", "Aaron")])
    assert df.height == 2
    assert set(df["key_mlbam"].to_list()) == {545361, 592450}


@pytest.mark.asyncio
@patch("polars_baseball.apis.playerid.get_lookup_table")
async def test_playerid_reverse_lookup(mock_get_table: MagicMock, mock_player_table: pl.DataFrame) -> None:
    mock_get_table.return_value = mock_player_table

    df = await playerid_reverse_lookup([545361, 592450], key_type=KeyType.MLBAM)
    assert df.height == 2
    assert set(df["name_last"].to_list()) == {"trout", "judge"}


# ── KeyType Enum Tests ────────────────────────────────────────────────────────


def test_key_type_enum_values() -> None:
    assert KeyType.MLBAM.value == "mlbam"
    assert KeyType.RETRO.value == "retro"
    assert KeyType.BBREF.value == "bbref"
    assert KeyType.FANGRAPHS.value == "fangraphs"


@pytest.mark.asyncio
@patch("polars_baseball.apis.playerid.get_lookup_table")
async def test_reverse_lookup_accepts_enum(mock_get_table: MagicMock, mock_player_table: pl.DataFrame) -> None:
    mock_get_table.return_value = mock_player_table

    df = await playerid_reverse_lookup([545361], key_type=KeyType.MLBAM)
    assert df.height == 1
    assert df["name_last"][0] == "trout"


@pytest.mark.asyncio
async def test_reverse_lookup_invalid_key_type_raises() -> None:
    with pytest.raises(InvalidParameterError, match="key_type must be a KeyType"):
        await playerid_reverse_lookup([545361], key_type=cast(KeyType, "invalid_key"))
