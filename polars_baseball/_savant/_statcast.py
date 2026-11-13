"""Baseball Savant and Statcast search and dataset mixin."""

from __future__ import annotations

import logging
import time
from collections.abc import Iterable, Sequence
from datetime import date, timedelta
from pathlib import Path
from typing import TYPE_CHECKING, Literal

import polars as pl

from polars_baseball._concurrency import bounded_gather
from polars_baseball._config import (
    DEFAULT_STATCAST_CONCURRENCY_LIMIT,
    SAVANT_STATCAST_SEARCH_URL,
    STATCAST_DATE_STEP,
    STATCAST_FIRST_YEAR,
    STATCAST_INCREMENTAL_OVERLAP_DAYS,
)
from polars_baseball._schemas.statcast import align_statcast_schemas
from polars_baseball._season import (
    get_baseball_eastern_yesterday,
    most_recent_season,
    sanitize_date_range,
    season_completion_threshold,
    statcast_date_range,
)
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


def _filter_replaced_dates(existing_df: pl.DataFrame, new_dfs: list[pl.DataFrame]) -> pl.DataFrame:
    """Drop rows from existing_df whose game_date is covered by new_dfs, preserving null dates."""
    if "game_date" not in existing_df.columns:
        return existing_df
    new_dates: set[str] = set()
    for new_df in new_dfs:
        if "game_date" in new_df.columns:
            new_dates.update(new_df["game_date"].drop_nulls().cast(pl.Utf8).unique().to_list())
    if not new_dates:
        return existing_df
    date_col_str = pl.col("game_date").cast(pl.Utf8)
    return existing_df.filter(pl.col("game_date").is_null() | ~date_col_str.is_in(new_dates))


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
        """Fetch Statcast pitch-level data from Baseball Savant for a given date range.

        Queries the Baseball Savant search endpoint across chunked date intervals
        and concatenates the results into a single Polars DataFrame.

        Parameters
        ----------
        start_date : str | date | None, default None
            First day of data to retrieve ('YYYY-MM-DD'). If both ``start_date`` and ``end_date``
            are omitted, defaults to yesterday. If omitted while ``end_date`` is provided,
            defaults to ``end_date`` (single-day query).
        end_date : str | date | None, default None
            Last day of data to retrieve ('YYYY-MM-DD'). If both ``start_date`` and ``end_date``
            are omitted, defaults to today. If omitted while ``start_date`` is provided,
            defaults to ``start_date`` (single-day query).
        team : str | None, default None
            Three-letter team abbreviation filter (e.g. 'NYY', 'BOS'). If None, all teams are returned.
        verbose : bool, default True
            Whether to display query progress bars (tqdm) and informative logger messages.
        parallel : bool, default True
            If True, chunks date ranges into concurrent HTTP requests bounded by ``concurrency_limit``.
            If False, requests are executed sequentially.
        concurrency_limit : int, default DEFAULT_STATCAST_CONCURRENCY_LIMIT (3)
            Maximum number of concurrent HTTP requests when ``parallel`` is True.

        Returns
        -------
        pl.DataFrame
            Concatenated and sorted Statcast pitch-by-pitch data. Returns an empty DataFrame
            if no pitch data exists for the query window.
        """
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
        valid_pk = _validate_game_pk(game_pk)
        url = _SC_SINGLE_GAME_REQUEST.format(game_pk=valid_pk)
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

    async def _sync_in_season_incremental(
        self,
        year: int,
        target_end: date,
        verbose: bool,
        concurrency_limit: int,
    ) -> Path | None:
        last_synced_str = self._dataset_gateway.partition_max_date(year)
        if last_synced_str is None:
            logger.warning("Partition max date for year %d could not be determined; falling back to full sync.", year)
            return None
        try:
            last_date = date.fromisoformat(last_synced_str)
        except ValueError:
            logger.warning(
                "Invalid date format in partition max date for year %d: %s; falling back to full sync.",
                year,
                last_synced_str,
            )
            return None

        if last_date >= target_end:
            return self._dataset_gateway.partition_path(year)

        incremental_start = max(last_date - timedelta(days=STATCAST_INCREMENTAL_OVERLAP_DAYS), date(year, 1, 1))
        date_range = list(statcast_date_range(incremental_start, target_end, step=STATCAST_DATE_STEP, verbose=False))
        if not date_range:
            if target_end >= date(year, 12, 31):
                self._dataset_gateway.mark_season_complete(year)
            return self._dataset_gateway.partition_path(year)

        existing_df = self._dataset_gateway.read_partition(year)
        if existing_df is None or existing_df.is_empty():
            logger.warning(
                "Existing partition for year %d cannot be read or is empty. "
                "Aborting incremental sync to prevent data loss; falling back to full sync.",
                year,
            )
            return None

        frames = await self._run_statcast_parallel(date_range, None, verbose, concurrency_limit)
        new_dfs = [df for df in frames if df is not None and not df.is_empty()]
        if not new_dfs:
            if target_end >= date(year, 12, 31):
                self._dataset_gateway.mark_season_complete(year)
            return self._dataset_gateway.partition_path(year)

        filtered_existing = _filter_replaced_dates(existing_df, new_dfs)
        all_dfs = [filtered_existing] + new_dfs
        df = pl.concat(align_statcast_schemas(all_dfs), how="diagonal")
        if "game_date" in df.columns:
            df = df.sort("game_date")
        path = await self._dataset_gateway.write_partition(year, df)
        if target_end >= date(year, 12, 31):
            self._dataset_gateway.mark_season_complete(year)
        return path

    async def _sync_season(
        self,
        year: int,
        force_update: bool,
        verbose: bool,
        concurrency_limit: int,
    ) -> Path:
        current_season = most_recent_season()
        yesterday = get_baseball_eastern_yesterday()
        season_end = date(year, 12, 31)
        target_end = min(yesterday, season_end)

        if force_update:
            self._dataset_gateway.clear_season_complete(year)
        elif self._dataset_gateway.year_exists(year):
            if year < current_season:
                if self._dataset_gateway.is_season_marked_complete(year):
                    return self._dataset_gateway.partition_path(year)
                completion_threshold = season_completion_threshold(year)
                max_synced_str = self._dataset_gateway.partition_max_date(year)
                is_complete = False
                if max_synced_str is not None:
                    try:
                        is_complete = date.fromisoformat(max_synced_str) >= completion_threshold
                    except ValueError:
                        is_complete = False
                if is_complete:
                    self._dataset_gateway.mark_season_complete(year)
                    return self._dataset_gateway.partition_path(year)
                logger.info(
                    "Historical partition for season %d is incomplete (max date: %s < %s); catching up.",
                    year,
                    max_synced_str,
                    completion_threshold,
                )
                incremental_path = await self._sync_in_season_incremental(year, season_end, verbose, concurrency_limit)
                if incremental_path is not None:
                    return incremental_path
            else:
                incremental_path = await self._sync_in_season_incremental(year, target_end, verbose, concurrency_limit)
                if incremental_path is not None:
                    return incremental_path

        start = date(year, 1, 1)
        stop = target_end if year >= current_season and target_end >= start else season_end
        date_range = list(statcast_date_range(start, stop, step=STATCAST_DATE_STEP, verbose=False))
        frames = await self._run_statcast_parallel(date_range, None, verbose, concurrency_limit)
        dfs = [df for df in frames if df is not None and not df.is_empty()]
        df = pl.concat(align_statcast_schemas(dfs), how="diagonal") if dfs else pl.DataFrame()
        if "game_date" in df.columns:
            df = df.sort("game_date")
        path = await self._dataset_gateway.write_partition(year, df)
        if year < current_season:
            self._dataset_gateway.mark_season_complete(year)
        return path

    async def sync_statcast(
        self,
        seasons: int | Sequence[int],
        force_update: bool = False,
        verbose: bool = True,
        concurrency_limit: int = DEFAULT_STATCAST_CONCURRENCY_LIMIT,
    ) -> list[Path]:
        """Scrape and persist full-season Statcast partitions to local compiled dataset.

        Historical completed seasons (prior to current season) that are complete through the end of
        the season are cached permanently unless ``force_update=True``. Active in-season datasets
        and incomplete historical partitions are automatically updated incrementally using a 2-day
        lookback overlap window aligned to US Eastern Time (triggered at most once per Eastern day
        once ``target_end`` is reached; late-finishing games synced in early Eastern hours will be
        corrected on the next day's sync).

        Parameters
        ----------
        seasons : int | Sequence[int]
            A single season year or a sequence of season years (e.g. 2023 or [2022, 2023]).
        force_update : bool, default False
            If True, ignores existing partitions and forces a full re-scrape of the entire season.
        verbose : bool, default True
            Whether to display progress bars during batch date scraping.
        concurrency_limit : int, default DEFAULT_STATCAST_CONCURRENCY_LIMIT (3)
            Maximum concurrent requests for scraping season chunks.

        Returns
        -------
        list[Path]
            Paths to the persisted Hive-partitioned Parquet files on disk.
        """
        years = _normalize_seasons(seasons)
        if years is None or not years:
            raise InvalidParameterError("sync_statcast requires at least one season.")

        paths: list[Path] = []
        for year in years:
            _validate_season(year)
            path = await self._sync_season(year, force_update, verbose, concurrency_limit)
            paths.append(path)
        return paths

    def _check_season_staleness(
        self,
        year: int,
        max_age: timedelta | None,
        current_season: int,
        target_end: date,
    ) -> Literal["force", "incremental", "fresh"]:
        path = self._dataset_gateway.partition_path(year)
        if max_age is not None and path.exists():
            mtime = path.stat().st_mtime
            if (time.time() - mtime) > max_age.total_seconds():
                return "force"

        if year < current_season and self._dataset_gateway.is_season_marked_complete(year):
            return "fresh"

        threshold = target_end if year >= current_season else season_completion_threshold(year)
        last_synced_str = self._dataset_gateway.partition_max_date(year)
        if last_synced_str is None:
            return "force"
        try:
            last_d = date.fromisoformat(last_synced_str)
            if last_d < threshold:
                return "incremental"
        except ValueError:
            return "force"
        return "fresh"

    async def _refresh_stale_seasons(
        self,
        years: list[int],
        missing: list[int],
        force_update: bool,
        max_age: timedelta | None,
    ) -> None:
        current_season = most_recent_season()
        yesterday = get_baseball_eastern_yesterday()
        force_years: list[int] = []
        incremental_years: list[int] = []

        for year in years:
            if year in missing:
                continue
            if force_update:
                force_years.append(year)
                continue
            target_end = min(yesterday, date(year, 12, 31))
            status = self._check_season_staleness(year, max_age, current_season, target_end)
            if status == "force":
                force_years.append(year)
            elif status == "incremental":
                incremental_years.append(year)

        if force_years:
            await self.sync_statcast(force_years, force_update=True)
        if incremental_years:
            await self.sync_statcast(incremental_years, force_update=False)

    async def scan_statcast(
        self,
        seasons: int | Sequence[int] | None = None,
        auto_download: bool = False,
        force_update: bool = False,
        max_age: timedelta | None = None,
    ) -> pl.LazyFrame:
        """Lazily scan the local Statcast Hive-partitioned Parquet dataset.

        Parameters
        ----------
        seasons : int | Sequence[int] | None, default None
            Specific season year(s) to query. If None, all locally available seasons are scanned.
        auto_download : bool, default False
            If True, automatically downloads missing seasons via ``sync_statcast()``. Also updates
            in-season or incomplete historical partitions, or partitions older than ``max_age``.
        force_update : bool, default False
            When combined with ``auto_download=True``, forces full re-download of the specified seasons.
        max_age : timedelta | None, default None
            Maximum acceptable cache age for partition files. If a partition's file age exceeds
            ``max_age`` and ``auto_download=True``, it is refreshed.

        Returns
        -------
        pl.LazyFrame
            Polars LazyFrame referencing the Parquet dataset with Hive partitioning enabled.
        """
        years = _normalize_seasons(seasons)
        if years is None:
            return self._dataset_gateway.scan(None)

        for year in years:
            _validate_season(year)

        synced = set(self._dataset_gateway.synced_seasons())
        missing = [year for year in years if year not in synced]
        if missing:
            if not auto_download:
                raise UpstreamUnavailableError(
                    f"No local Statcast partition for season(s): {sorted(missing)}. "
                    "Run sync_statcast() or pass auto_download=True."
                )
            await self.sync_statcast(missing, force_update=force_update)

        if auto_download:
            await self._refresh_stale_seasons(years, missing, force_update, max_age)

        return self._dataset_gateway.scan(years)
