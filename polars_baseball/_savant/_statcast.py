"""Baseball Savant and Statcast search and dataset mixin."""

from __future__ import annotations

import logging
from collections.abc import Iterable, Sequence
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING, Literal

import polars as pl

from polars_baseball._concurrency import bounded_gather
from polars_baseball._config import (
    DEFAULT_STATCAST_CONCURRENCY_LIMIT,
    SAVANT_STATCAST_SEARCH_URL,
    STATCAST_DATE_STEP,
    STATCAST_FIRST_YEAR,
)
from polars_baseball._schemas.statcast import align_statcast_schemas
from polars_baseball._season import most_recent_season, sanitize_date_range, statcast_date_range
from polars_baseball.exceptions import (
    InvalidParameterError,
    UpstreamUnavailableError,
)

if TYPE_CHECKING:
    from polars_baseball.client import BaseballClient
    from polars_baseball.gateways.savant import SavantGateway
    from polars_baseball.gateways.statcast_dataset import StatcastDatasetGateway

logger = logging.getLogger(__name__)

_SC_SINGLE_GAME_REQUEST = f"{SAVANT_STATCAST_SEARCH_URL}?all=true&type=details&game_pk={{game_pk}}"
_BASE_SC_PARAMS: dict[str, str] = {
    "all": "true",
    "hfPT": "",
    "hfAB": "",
    "hfBBT": "",
    "hfPR": "",
    "hfZ": "",
    "stadium": "",
    "hfBBL": "",
    "hfNewZones": "",
    "hfGT": "R|PO|S|=",
    "hfSea": "",
    "hfSit": "",
    "hfOuts": "",
    "opponent": "",
    "pitcher_throws": "",
    "batter_stands": "",
    "hfSA": "",
    "position": "",
    "hfRO": "",
    "home_road": "",
    "hfFlag": "",
    "metric_1": "",
    "hfInn": "",
    "min_pitches": "0",
    "min_results": "0",
    "group_by": "name",
    "sort_col": "pitches",
    "player_event_sort": "h_launch_speed",
    "sort_order": "desc",
    "min_abs": "0",
    "type": "details",
}

_SORT_COLS = ["game_date", "game_pk", "at_bat_number", "pitch_number"]


def _check_player_id(player_id: int | None) -> int:
    if player_id is None:
        raise InvalidParameterError(
            "Player ID is required. If you need to find a player's id, try "
            "client.lookup.playerid_lookup(last_name, first_name) and use their key_mlbam. "
            "If you want statcast data for all players, try the statcast() method."
        )
    return player_id


def _sort_statcast(df: pl.DataFrame) -> pl.DataFrame:
    existing = [c for c in _SORT_COLS if c in df.columns]
    if existing:
        return df.sort(existing, descending=True)
    return df


def _validate_game_pk(game_pk: int | str) -> int:
    if isinstance(game_pk, int) and not isinstance(game_pk, bool):
        return game_pk
    if isinstance(game_pk, str) and game_pk.strip().isdigit():
        return int(game_pk.strip())
    raise InvalidParameterError(f"game_pk must be an integer or integer string, got {game_pk!r}")


def _normalize_seasons(seasons: int | Sequence[int] | None) -> list[int] | None:
    if seasons is None:
        return None
    if isinstance(seasons, int):
        return [seasons]
    return list(seasons)


def _validate_season(year: int) -> None:
    max_year = most_recent_season()
    if year < STATCAST_FIRST_YEAR or year > max_year:
        raise InvalidParameterError(
            f"Season {year} is out of range; Statcast data is available for {STATCAST_FIRST_YEAR}-{max_year}."
        )


class SavantStatcastMixin:
    """Methods for Statcast pitch searches, single-game lookups, and dataset management."""

    _client: BaseballClient
    _gateway: SavantGateway
    _dataset_gateway: StatcastDatasetGateway

    async def _small_request(
        self,
        start_dt: date,
        end_dt: date,
        team: str | None = None,
    ) -> pl.DataFrame:
        params: dict[str, str] = {
            **_BASE_SC_PARAMS,
            "player_type": "pitcher",
            "game_date_gt": str(start_dt),
            "game_date_lt": str(end_dt),
            "team": team if team else "",
        }
        return await self._gateway.get_dataset(
            SAVANT_STATCAST_SEARCH_URL,
            params=params,
        )

    async def _player_request(
        self,
        start_dt: date,
        end_dt: date,
        player_id: int,
        player_type: str,
    ) -> pl.DataFrame:
        lookup_key = "batters_lookup[]" if player_type == "batter" else "pitchers_lookup[]"
        params: dict[str, str] = {
            **_BASE_SC_PARAMS,
            "player_type": player_type,
            "game_date_gt": str(start_dt),
            "game_date_lt": str(end_dt),
            lookup_key: str(player_id),
            "team": "",
        }
        return await self._gateway.get_dataset(
            SAVANT_STATCAST_SEARCH_URL,
            params=params,
        )

    async def _run_statcast_parallel(
        self,
        date_range: list[tuple[date, date]],
        team: str | None,
        verbose: bool,
        concurrency_limit: int,
    ) -> list[pl.DataFrame]:
        tasks = [lambda s=start, e=end: self._small_request(s, e, team) for start, end in date_range]
        if verbose and len(date_range) > 1:
            from tqdm import tqdm

            with tqdm(total=len(date_range)) as pbar:
                return await bounded_gather(
                    tasks,
                    concurrency_limit=concurrency_limit,
                    on_progress=lambda: pbar.update(1),
                )
        return await bounded_gather(tasks, concurrency_limit=concurrency_limit)

    async def _run_statcast_sequential(
        self,
        date_range: list[tuple[date, date]],
        team: str | None,
        verbose: bool,
    ) -> list[pl.DataFrame]:
        dataframe_list: list[pl.DataFrame] = []
        iterable: Iterable[tuple[date, date]] = date_range
        if verbose and len(date_range) > 1:
            from tqdm import tqdm

            iterable = tqdm(date_range)
        for start, end in iterable:
            dataframe_list.append(await self._small_request(start, end, team))
        return dataframe_list

    async def statcast(
        self,
        start_date: str | date | None = None,
        end_date: str | date | None = None,
        team: str | None = None,
        verbose: bool = True,
        parallel: bool = True,
        concurrency_limit: int = DEFAULT_STATCAST_CONCURRENCY_LIMIT,
    ) -> pl.DataFrame:
        """Fetch Statcast pitch-level data for a date range."""
        start_dt_date, end_dt_date = sanitize_date_range(start_date, end_date)

        if verbose:
            logger.info("This is a large query, it may take a moment to complete")

        date_range = list(statcast_date_range(start_dt_date, end_dt_date, step=STATCAST_DATE_STEP, verbose=verbose))

        if parallel:
            dataframe_list = await self._run_statcast_parallel(date_range, team, verbose, concurrency_limit)
        else:
            dataframe_list = await self._run_statcast_sequential(date_range, team, verbose)

        dfs = [df for df in dataframe_list if df is not None and not df.is_empty()]
        if not dfs:
            return pl.DataFrame()

        final_df = pl.concat(align_statcast_schemas(dfs), how="diagonal")
        return _sort_statcast(final_df)

    async def single_game(self, game_pk: str | int) -> pl.DataFrame:
        """Fetch Statcast data for a single game."""
        url = _SC_SINGLE_GAME_REQUEST.format(game_pk=game_pk)
        df = await self._gateway.get_dataset(url)
        if df.is_empty():
            return pl.DataFrame()
        return _sort_statcast(df)

    async def _statcast_player(
        self,
        player_type: Literal["batter", "pitcher"],
        start_dt: str | date | None,
        end_dt: str | date | None,
        player_id: int | None,
    ) -> pl.DataFrame:
        pid = _check_player_id(player_id)
        start_dt_date, end_dt_date = sanitize_date_range(start_dt, end_dt)
        dfs = []
        curr = start_dt_date
        while curr <= end_dt_date:
            year_end = min(date(curr.year, 12, 31), end_dt_date)
            chunk = await self._player_request(curr, year_end, pid, player_type)
            if not chunk.is_empty():
                dfs.append(chunk)
            curr = date(curr.year + 1, 1, 1)
        if not dfs:
            return pl.DataFrame()
        return _sort_statcast(pl.concat(align_statcast_schemas(dfs), how="diagonal"))

    async def batter(
        self,
        start_date: str | date | None = None,
        end_date: str | date | None = None,
        player_id: int | None = None,
    ) -> pl.DataFrame:
        """Fetch Statcast data for a specific batter."""
        return await self._statcast_player("batter", start_date, end_date, player_id)

    async def pitcher(
        self,
        start_date: str | date | None = None,
        end_date: str | date | None = None,
        player_id: int | None = None,
    ) -> pl.DataFrame:
        """Fetch Statcast data for a specific pitcher."""
        return await self._statcast_player("pitcher", start_date, end_date, player_id)

    async def sync_statcast(
        self,
        seasons: int | Sequence[int],
        force_update: bool = False,
        verbose: bool = True,
        concurrency_limit: int = DEFAULT_STATCAST_CONCURRENCY_LIMIT,
    ) -> list[Path]:
        """Scrape and persist full-season Statcast partitions to local compiled dataset."""
        years = _normalize_seasons(seasons)
        if years is None or not years:
            raise InvalidParameterError("sync_statcast requires at least one season.")

        paths: list[Path] = []
        for year in years:
            _validate_season(year)
            if self._dataset_gateway.year_exists(year) and not force_update:
                paths.append(self._dataset_gateway.partition_path(year))
                continue
            start = date(year, 1, 1)
            stop = date(year, 12, 31)
            date_range = list(statcast_date_range(start, stop, step=STATCAST_DATE_STEP, verbose=False))
            frames = await self._run_statcast_parallel(date_range, None, verbose, concurrency_limit)
            dfs = [df for df in frames if df is not None and not df.is_empty()]
            df = pl.concat(align_statcast_schemas(dfs), how="diagonal") if dfs else pl.DataFrame()
            paths.append(await self._dataset_gateway.write_partition(year, df))
        return paths

    async def scan_statcast(
        self,
        seasons: int | Sequence[int] | None = None,
        auto_download: bool = False,
    ) -> pl.LazyFrame:
        """Lazily scan the local Statcast Hive-partitioned Parquet dataset."""
        years = _normalize_seasons(seasons)
        if years is not None:
            for year in years:
                _validate_season(year)
            synced = set(self._dataset_gateway.synced_seasons())
            missing = [year for year in years if year not in synced]
            if missing:
                if auto_download:
                    await self.sync_statcast(missing)
                else:
                    raise UpstreamUnavailableError(
                        f"No local Statcast partition for season(s): {sorted(missing)}. "
                        "Run sync_statcast() or pass auto_download=True."
                    )
        return self._dataset_gateway.scan(years)
