import asyncio
import logging
import threading
import unicodedata
import weakref
from collections.abc import Awaitable, Callable
from difflib import get_close_matches

import polars as pl

from polars_baseball._config import (
    FUZZY_FALLBACK_MIN_RESULTS,
    FUZZY_MATCH_CUTOFF,
    FUZZY_MATCH_LIMIT,
    FUZZY_MIN_SIZE_FOR_FILTER,
    FUZZY_NAME_LENGTH_TOLERANCE,
)
from polars_baseball.enums.player import KeyType
from polars_baseball.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)
LookupTableLoader = Callable[[], Awaitable[pl.DataFrame]]
PlayerId = int | str
_NORMALIZED_LAST_COLUMN = "name_last_normalized"
_NORMALIZED_FIRST_COLUMN = "name_first_normalized"
_NORMALIZED_COLUMNS = (_NORMALIZED_LAST_COLUMN, _NORMALIZED_FIRST_COLUMN)


def normalize_accents(value: str) -> str:
    """Remove Unicode combining marks from a player name."""
    if not value:
        return ""
    return "".join(c for c in unicodedata.normalize("NFD", value) if unicodedata.category(c) != "Mn")


def _without_normalized_names(table: pl.DataFrame) -> pl.DataFrame:
    return table.drop(*_NORMALIZED_COLUMNS)


def _fuzzy_candidates(last: str, table: pl.DataFrame, last_column: str = "name_last") -> pl.DataFrame:
    if table.height <= FUZZY_MIN_SIZE_FOR_FILTER:
        return table
    last_length = len(last)
    candidates = table.filter(
        (pl.col(last_column).str.len_chars() >= max(1, last_length - FUZZY_NAME_LENGTH_TOLERANCE))
        & (pl.col(last_column).str.len_chars() <= last_length + FUZZY_NAME_LENGTH_TOLERANCE)
    )
    return table if candidates.height < FUZZY_FALLBACK_MIN_RESULTS else candidates


def get_closest_names(
    last: str,
    first: str,
    table: pl.DataFrame,
    last_column: str = "name_last",
    first_column: str = "name_first",
) -> pl.DataFrame:
    """Return fuzzy name matches from a normalized player lookup table."""
    filled = table.with_columns(
        chadwick_name=pl.col(first_column).fill_null("") + " " + pl.col(last_column).fill_null("")
    )
    candidates = _fuzzy_candidates(last, filled, last_column)
    matches = get_close_matches(
        f"{first} {last}",
        candidates["chadwick_name"].to_list(),
        n=FUZZY_MATCH_LIMIT,
        cutoff=FUZZY_MATCH_CUTOFF,
    )
    return candidates.filter(pl.col("chadwick_name").is_in(matches)).drop("chadwick_name")


class PlayerLookupService:
    def __init__(self, load_table: LookupTableLoader) -> None:
        self._load_table = load_table
        self.table: pl.DataFrame | None = None
        self._load_locks: weakref.WeakKeyDictionary[asyncio.AbstractEventLoop, asyncio.Lock] = (
            weakref.WeakKeyDictionary()
        )
        self._load_locks_guard = threading.Lock()

    def _load_lock(self) -> asyncio.Lock:
        loop = asyncio.get_running_loop()
        with self._load_locks_guard:
            lock = self._load_locks.get(loop)
            if lock is None:
                lock = asyncio.Lock()
                self._load_locks[loop] = lock
            return lock

    async def _ensure_table(self) -> pl.DataFrame:
        if self.table is not None:
            return self.table
        async with self._load_lock():
            if self.table is not None:
                return self.table
            table = await self._load_table()
            self.table = table.with_columns(
                pl.col("name_last")
                .str.normalize("NFD")
                .str.replace_all(r"[\u0300-\u036f]", "")
                .alias(_NORMALIZED_LAST_COLUMN),
                pl.col("name_first")
                .str.normalize("NFD")
                .str.replace_all(r"[\u0300-\u036f]", "")
                .alias(_NORMALIZED_FIRST_COLUMN),
            )
            return self.table

    async def search(
        self, last: str, first: str | None = None, fuzzy: bool = False, ignore_accents: bool = False
    ) -> pl.DataFrame:
        last_clean = last.lower()
        first_clean = first.lower() if first else None
        table = await self._ensure_table()
        last_column = "name_last"
        first_column = "name_first"
        if ignore_accents:
            last_clean = normalize_accents(last_clean)
            first_clean = normalize_accents(first_clean) if first_clean else None
            last_column = _NORMALIZED_LAST_COLUMN
            first_column = _NORMALIZED_FIRST_COLUMN
        predicate = pl.col(last_column) == last_clean
        if first_clean is not None:
            predicate &= pl.col(first_column) == first_clean
        results = table.filter(predicate)
        if not results.is_empty() or not fuzzy:
            return _without_normalized_names(results)
        logger.warning("No names found. Returning closest Chadwick register matches.")
        matches = get_closest_names(last_clean, first_clean or "", table, last_column, first_column)
        return _without_normalized_names(matches)

    async def search_list(self, players: list[tuple[str, str]]) -> pl.DataFrame:
        results = [await self.search(last, first) for last, first in players]
        return pl.concat(results, how="diagonal") if results else pl.DataFrame()

    async def reverse_lookup(self, player_ids: list[PlayerId], key_type: KeyType = KeyType.MLBAM) -> pl.DataFrame:
        if not isinstance(key_type, KeyType):
            raise InvalidParameterError("key_type must be a KeyType enum value.")
        key = f"key_{key_type.value}"
        ids: list[PlayerId] = player_ids
        if key_type not in (KeyType.MLBAM, KeyType.FANGRAPHS):
            ids = [str(player_id) for player_id in player_ids]
        results = (await self._ensure_table()).filter(pl.col(key).is_in(ids))
        return _without_normalized_names(results)
