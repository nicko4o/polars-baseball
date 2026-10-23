"""Cross-provider lookup and mapping client for players and teams."""

from __future__ import annotations

import logging
import warnings
from importlib.resources import files as resources_files
from pathlib import Path
from typing import TYPE_CHECKING, Final

import polars as pl

from polars_baseball._config import CHADWICK_REGISTER_ARCHIVE_URL
from polars_baseball._player_lookup import PlayerId, PlayerLookupService
from polars_baseball._schema_utils import validate_and_cast_schema
from polars_baseball.enums.player import KeyType
from polars_baseball.exceptions import ServerError, UpstreamParseError
from polars_baseball.gateways.compiled import CompiledDatasetGateway, CompiledTable

if TYPE_CHECKING:
    from polars_baseball.client import BaseballClient

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

TEAM_IDS_REQUIRED: list[str] = ["lgID", "teamID", "yearID"]
TEAM_IDS_TYPES: dict[str, pl.DataType | type[pl.DataType]] = {
    "lgID": pl.String,
    "teamID": pl.String,
    "yearID": pl.Int64,
}

_DATA_DIR = Path(str(resources_files("polars_baseball").joinpath("data")))
_DATA_FILENAME = _DATA_DIR / "fangraphs_teams.csv"


def _chadwick_people_table() -> CompiledTable:
    return CompiledTable(
        dataset=CHADWICK_REGISTER_DATASET,
        table_name=CHADWICK_PEOPLE_TABLE,
        archive_url=CHADWICK_REGISTER_ARCHIVE_URL,
        archive_member_pattern=CHADWICK_PEOPLE_FILE_PATTERN,
    )


def _add_missing_lookup_columns(table: pl.DataFrame) -> pl.DataFrame:
    missing = [
        pl.lit(None, dtype=dtype).alias(column)
        for column, dtype in PLAYER_LOOKUP_SCHEMA.items()
        if column not in table.columns
    ]
    return table.with_columns(missing) if missing else table


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


def _read_team_ids(season: int | None = None, league: str = "ALL") -> pl.DataFrame:
    if not _DATA_FILENAME.exists():
        raise ServerError(f"Team ID data file not found at {_DATA_FILENAME}")

    df = pl.read_csv(_DATA_FILENAME)
    df = validate_and_cast_schema(df, TEAM_IDS_REQUIRED, TEAM_IDS_TYPES)

    if season is not None:
        df = df.filter(pl.col("yearID") == season)

    if league is not None and league.upper() != "ALL":
        df = df.filter(pl.col("lgID") == league.upper())

    return df


class LookupClient:
    """Namespaced Player and Team lookup client."""

    def __init__(self, client: BaseballClient) -> None:
        self._client = client
        self._gateway = CompiledDatasetGateway(client)
        self._service = PlayerLookupService(lambda _ctx: self.get_lookup_table(save=True))

    def reset(self) -> None:
        """Reset cached player lookup table in memory."""
        self._service.reset()

    async def chadwick_register(self, save: bool = True) -> pl.DataFrame:
        """Fetch the raw Chadwick Baseball Register dataset."""
        logger.info("Gathering player lookup table from Chadwick register gateway.")
        raw = await self._gateway.read_table(_chadwick_people_table(), use_cache=save)
        return _normalize_chadwick_register(raw)

    async def get_lookup_table(self, save: bool = True) -> pl.DataFrame:
        """Fetch the Chadwick register with lowercased name_last and name_first columns."""
        table = await self.chadwick_register(save=save)
        if table.is_empty():
            return table
        return table.with_columns(
            pl.col("name_last").str.to_lowercase(),
            pl.col("name_first").str.to_lowercase(),
        )

    async def playerid_lookup(
        self,
        last: str,
        first: str | None = None,
        ignore_accents: bool = False,
    ) -> pl.DataFrame:
        """Lookup a player by last (and optionally first) name."""
        df = await self._service.search(last, first, ignore_accents, context=self._client)
        if df.is_empty():
            warnings.warn(
                "No player found for the given name. Check the spelling or use "
                "client.lookup.player_name_suggestions(last, first) for fuzzy matches.",
                UserWarning,
                stacklevel=2,
            )
        return df

    async def player_name_suggestions(
        self,
        last: str,
        first: str | None = None,
        ignore_accents: bool = False,
    ) -> pl.DataFrame:
        """Return fuzzy player name suggestions without treating them as exact lookup results."""
        return await self._service.suggest(last, first, ignore_accents, context=self._client)

    async def player_search_list(
        self,
        player_list: list[tuple[str, str]],
    ) -> pl.DataFrame:
        """Batch lookup for multiple player name pairs."""
        return await self._service.search_list(player_list, context=self._client)

    async def playerid_reverse_lookup(
        self,
        player_ids: list[PlayerId],
        key_type: KeyType = KeyType.MLBAM,
    ) -> pl.DataFrame:
        """Reverse lookup players by their IDs in a given key system."""
        return await self._service.reverse_lookup(player_ids, key_type, context=self._client)

    def team_ids(self, season: int | None = None, league: str = "ALL") -> pl.DataFrame:
        """Fetch team identifiers from bundled FanGraphs team data."""
        return _read_team_ids(season=season, league=league)


__all__ = ["LookupClient"]
