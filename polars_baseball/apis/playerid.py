import logging
import unicodedata
from difflib import get_close_matches
from typing import Final

import polars as pl

from polars_baseball._config import (
    CHADWICK_REGISTER_ARCHIVE_URL,
    FUZZY_FALLBACK_MIN_RESULTS,
    FUZZY_MATCH_CUTOFF,
    FUZZY_MATCH_LIMIT,
    FUZZY_MIN_SIZE_FOR_FILTER,
    FUZZY_NAME_LENGTH_TOLERANCE,
)
from polars_baseball.context import BaseballContext, default_context
from polars_baseball.enums.player import KeyType
from polars_baseball.exceptions import InvalidParameterError, UpstreamParseError
from polars_baseball.gateways.compiled import CompiledDatasetGateway, CompiledTable

logger = logging.getLogger(__name__)

PLAYER_LOOKUP_SCHEMA: Final[dict[str, type[pl.DataType]]] = {
    "name_last": pl.String,
    "name_first": pl.String,
    "key_mlbam": pl.Int64,
    "key_retro": pl.String,
    "key_bbref": pl.String,
    "key_fangraphs": pl.Int64,
    "mlb_played_first": pl.Float64,
    "mlb_played_last": pl.Float64,
}

CHADWICK_REGISTER_DATASET: Final[str] = "chadwick-register"
CHADWICK_PEOPLE_TABLE: Final[str] = "people"
CHADWICK_PEOPLE_FILE_PATTERN: Final[str] = r"/people.+csv$"

_MISSING_ID: Final[int] = -1
_CHADWICK_MLB_ONLY_COLUMNS: Final[tuple[str, ...]] = (
    "key_retro",
    "key_bbref",
    "key_fangraphs",
    "mlb_played_first",
    "mlb_played_last",
)


def normalize_accents(s: str) -> str:
    """Strip Unicode combining diacritical marks (accents) from a string.

    Used internally for fuzzy name matching when ``ignore_accents`` is enabled.
    Returns an empty string when input is empty or falsy.
    """
    if not s:
        return ""
    return "".join(c for c in unicodedata.normalize("NFD", s) if unicodedata.category(c) != "Mn")


def _chadwick_people_table() -> CompiledTable:
    return CompiledTable(
        dataset=CHADWICK_REGISTER_DATASET,
        table_name=CHADWICK_PEOPLE_TABLE,
        archive_url=CHADWICK_REGISTER_ARCHIVE_URL,
        archive_member_pattern=CHADWICK_PEOPLE_FILE_PATTERN,
    )


def _add_missing_lookup_columns(table: pl.DataFrame) -> pl.DataFrame:
    result = table
    for column, dtype in PLAYER_LOOKUP_SCHEMA.items():
        if column not in result.columns:
            result = result.with_columns(pl.lit(None).cast(dtype).alias(column))
    return result


def _normalize_chadwick_register(table: pl.DataFrame) -> pl.DataFrame:
    if table.is_empty():
        raise UpstreamParseError("Chadwick people table is empty.")

    normalized = _add_missing_lookup_columns(table)
    normalized = normalized.filter(pl.any_horizontal([pl.col(c).is_not_null() for c in _CHADWICK_MLB_ONLY_COLUMNS]))
    normalized = normalized.with_columns(
        pl.col("key_mlbam").fill_null(_MISSING_ID).cast(pl.Int64),
        pl.col("key_fangraphs").fill_null(_MISSING_ID).cast(pl.Int64),
    )
    return normalized.select(list(PLAYER_LOOKUP_SCHEMA.keys()))


async def _fetch_and_parse_chadwick(ctx: BaseballContext, *, use_cache: bool = True) -> pl.DataFrame:
    logger.info("Gathering player lookup table from Chadwick register gateway.")
    raw = await CompiledDatasetGateway(ctx).read_table(_chadwick_people_table(), use_cache=use_cache)
    return _normalize_chadwick_register(raw)


async def chadwick_register(save: bool = True, context: BaseballContext | None = None) -> pl.DataFrame:
    """Fetch the raw Chadwick Baseball Register dataset.

    Returns a DataFrame with columns ``name_last``, ``name_first``, ``key_mlbam``,
    ``key_retro``, ``key_bbref``, ``key_fangraphs``, ``mlb_played_first``,
    ``mlb_played_last``.  Only rows with at least one MLB key are included.

    Edge Cases:
        - Raises ``UpstreamParseError`` if the upstream people table is empty.
        - Missing MLB IDs default to ``-1``.
    """
    ctx = context or default_context()
    return await _fetch_and_parse_chadwick(ctx, use_cache=save)


async def get_lookup_table(save: bool = True, context: BaseballContext | None = None) -> pl.DataFrame:
    """Fetch the Chadwick register with lowercased ``name_last`` and ``name_first`` columns.

    Wraps :func:`chadwick_register` and applies ``str.to_lowercase()`` on name columns.
    """
    table = await chadwick_register(save, context)
    if table.is_empty():
        return table
    return table.with_columns(
        pl.col("name_last").str.to_lowercase(),
        pl.col("name_first").str.to_lowercase(),
    )


def get_closest_names(last: str, first: str, player_table: pl.DataFrame) -> pl.DataFrame:
    """Filter the player table to names that are fuzzy matches against a given name.

    Uses ``difflib.get_close_matches`` with the configured cutoff and limit constants.

    Edge Cases:
        - Returns empty DataFrame when no close matches are found.
    """
    filled = player_table.with_columns(
        name_first=pl.col("name_first").fill_null(""),
        name_last=pl.col("name_last").fill_null(""),
    ).with_columns(chadwick_name=pl.col("name_first") + " " + pl.col("name_last"))

    candidate_table = _fuzzy_candidates(last, filled)
    names_list = candidate_table["chadwick_name"].to_list()
    matches = get_close_matches(
        f"{first} {last}",
        names_list,
        n=FUZZY_MATCH_LIMIT,
        cutoff=FUZZY_MATCH_CUTOFF,
    )
    return candidate_table.filter(pl.col("chadwick_name").is_in(matches)).drop("chadwick_name")


def _fuzzy_candidates(last: str, player_table: pl.DataFrame) -> pl.DataFrame:
    if player_table.height <= FUZZY_MIN_SIZE_FOR_FILTER:
        return player_table

    len_last = len(last)
    candidates = player_table.filter(
        (pl.col("name_last").str.len_chars() >= max(1, len_last - FUZZY_NAME_LENGTH_TOLERANCE))
        & (pl.col("name_last").str.len_chars() <= len_last + FUZZY_NAME_LENGTH_TOLERANCE)
    )
    if candidates.height < FUZZY_FALLBACK_MIN_RESULTS:
        return player_table
    return candidates


class _PlayerSearchClient:
    def __init__(self) -> None:
        self.table: pl.DataFrame | None = None

    async def _ensure_table(self) -> pl.DataFrame:
        if self.table is not None:
            return self.table

        table = await get_lookup_table()
        if table.is_empty():
            self.table = table
            return self.table

        self.table = table.with_columns(
            pl.col("name_last")
            .str.normalize("NFD")
            .str.replace_all(r"[\u0300-\u036f]", "")
            .alias("name_last_normalized"),
            pl.col("name_first")
            .str.normalize("NFD")
            .str.replace_all(r"[\u0300-\u036f]", "")
            .alias("name_first_normalized"),
        )
        return self.table

    async def search(
        self,
        last: str,
        first: str | None = None,
        fuzzy: bool = False,
        ignore_accents: bool = False,
    ) -> pl.DataFrame:
        last_clean = last.lower()
        first_clean = first.lower() if first else None
        table_search = await self._ensure_table()

        if ignore_accents:
            last_clean = normalize_accents(last_clean)
            first_clean = normalize_accents(first_clean) if first_clean else None
            table_search = table_search.with_columns(
                pl.col("name_last_normalized").alias("name_last"),
                pl.col("name_first_normalized").alias("name_first"),
            )

        if first_clean is None:
            results = table_search.filter(pl.col("name_last") == last_clean)
        else:
            results = table_search.filter((pl.col("name_last") == last_clean) & (pl.col("name_first") == first_clean))

        if results.is_empty() and fuzzy:
            logger.warning("No names found. Returning closest Chadwick register matches.")
            return get_closest_names(last_clean, first_clean or "", table_search)
        return results

    async def search_list(self, player_list: list[tuple[str, str]]) -> pl.DataFrame:
        dfs: list[pl.DataFrame] = []
        for last, first in player_list:
            dfs.append(await self.search(last, first))
        if not dfs:
            return pl.DataFrame()
        return pl.concat(dfs, how="diagonal")

    async def reverse_lookup(self, player_ids: list[int], key_type: KeyType = KeyType.MLBAM) -> pl.DataFrame:
        if not isinstance(key_type, KeyType):
            raise InvalidParameterError("key_type must be a KeyType enum value.")

        key = f"key_{key_type.value}"
        target_ids: list[int] | list[str]
        if key_type in (KeyType.MLBAM, KeyType.FANGRAPHS):
            target_ids = player_ids
        else:
            target_ids = [str(x) for x in player_ids]
        table = await self._ensure_table()
        return table.filter(pl.col(key).is_in(target_ids))


_module_client = _PlayerSearchClient()


async def playerid_lookup(
    last: str,
    first: str | None = None,
    fuzzy: bool = False,
    ignore_accents: bool = False,
) -> pl.DataFrame:
    """Lookup a player by last (and optionally first) name.

    Exact match is attempted first.  When ``fuzzy`` is true and exact match produces no
    results, falls back to ``difflib``-based fuzzy matching.  When ``ignore_accents`` is
    true, diacritical marks are normalized before comparison.

    Edge Cases:
        - Returns empty DataFrame when no player matches the criteria.
        - Case-insensitive; inputs are lowercased automatically.
    """
    return await _module_client.search(last, first, fuzzy, ignore_accents)


async def player_search_list(player_list: list[tuple[str, str]]) -> pl.DataFrame:
    """Batch lookup for multiple player name pairs.

    Each tuple is ``(last, first)``.  Delegates to :func:`playerid_lookup` for each pair
    and concatenates results.

    Edge Cases:
        - Returns empty DataFrame when the input list is empty or no players match.
    """
    return await _module_client.search_list(player_list)


async def playerid_reverse_lookup(player_ids: list[int], key_type: KeyType = KeyType.MLBAM) -> pl.DataFrame:
    """Reverse lookup players by their IDs in a given key system.

    Use ``key_type`` to select the ID namespace (MLBAM, FanGraphs, BRef, or Retrosheet).
    Raises ``InvalidParameterError`` when ``key_type`` is not a ``KeyType`` enum.

    Edge Cases:
        - Returns empty DataFrame when none of the provided IDs match.
    """
    return await _module_client.reverse_lookup(player_ids, key_type)
