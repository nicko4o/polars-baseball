import asyncio
from unittest.mock import AsyncMock

import polars as pl
import pytest

from polars_baseball._player_lookup import PlayerLookupService
from polars_baseball.enums.player import KeyType


def _player_table() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "name_last": ["valenzuéla", "trout"],
            "name_first": ["fernando", "mike"],
            "key_mlbam": [123617, 545361],
            "key_retro": ["valef001", "troum001"],
            "key_bbref": ["valenfe01", "troutmi01"],
            "key_fangraphs": [1011, 10155],
        }
    )


@pytest.mark.asyncio
async def test_concurrent_initialization_loads_table_once() -> None:
    async def load_table() -> pl.DataFrame:
        await asyncio.sleep(0)
        return _player_table()

    loader = AsyncMock(side_effect=load_table)
    service = PlayerLookupService(loader)

    results = await asyncio.gather(*(service.search("trout") for _ in range(3)))

    assert loader.await_count == 1
    assert all(result.height == 1 for result in results)


@pytest.mark.asyncio
async def test_failed_initialization_can_retry() -> None:
    loader = AsyncMock(side_effect=[RuntimeError("load failed"), _player_table()])
    service = PlayerLookupService(loader)

    with pytest.raises(RuntimeError, match="load failed"):
        await service.search("trout")

    assert (await service.search("trout")).height == 1
    assert loader.await_count == 2


@pytest.mark.asyncio
async def test_empty_table_with_lookup_schema_is_searchable() -> None:
    empty_table = _player_table().clear()
    service = PlayerLookupService(AsyncMock(return_value=empty_table))

    result = await service.search("nobody", ignore_accents=True)

    assert result.is_empty()
    assert result.schema == empty_table.schema


@pytest.mark.asyncio
async def test_accent_insensitive_search_preserves_original_names() -> None:
    service = PlayerLookupService(AsyncMock(return_value=_player_table()))

    result = await service.search("valenzuela", "fernando", ignore_accents=True)

    assert result["name_last"].item() == "valenzuéla"


@pytest.mark.asyncio
async def test_search_does_not_return_fuzzy_suggestions_as_results() -> None:
    service = PlayerLookupService(AsyncMock(return_value=_player_table()))

    with pytest.warns(DeprecationWarning, match="fuzzy=True no longer returns suggestions"):
        result = await service.search("valenzula", "fernando", fuzzy=True, ignore_accents=True)

    assert result.is_empty()


@pytest.mark.asyncio
async def test_suggest_accent_insensitive_search_preserves_original_names() -> None:
    service = PlayerLookupService(AsyncMock(return_value=_player_table()))

    result = await service.suggest("valenzula", "fernando", ignore_accents=True)

    assert "valenzuéla" in result["name_last"].to_list()


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("key_type", "player_id"),
    [
        (KeyType.BBREF, "troutmi01"),
        (KeyType.RETRO, "troum001"),
        (KeyType.MLBAM, "545361"),
        (KeyType.MLBAM, 545361),
        (KeyType.FANGRAPHS, "10155"),
        (KeyType.FANGRAPHS, 10155),
    ],
)
async def test_reverse_lookup_accepts_string_and_int_ids(key_type: KeyType, player_id: str | int) -> None:
    service = PlayerLookupService(AsyncMock(return_value=_player_table()))

    result = await service.reverse_lookup([player_id], key_type)

    assert result["name_last"].to_list() == ["trout"]


@pytest.mark.asyncio
async def test_reverse_lookup_invalid_integer_id_raises_error() -> None:
    from polars_baseball.exceptions import InvalidParameterError

    service = PlayerLookupService(AsyncMock(return_value=_player_table()))

    with pytest.raises(InvalidParameterError, match="Invalid integer player ID"):
        await service.reverse_lookup(["invalid_id"], KeyType.MLBAM)
