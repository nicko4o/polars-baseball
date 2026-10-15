"""Namespaced client for Baseball Savant and Statcast endpoints."""

from __future__ import annotations

import logging
import warnings
from collections.abc import Awaitable, Callable, Iterable, Mapping, Sequence
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING, Literal

import polars as pl

from polars_baseball._concurrency import bounded_gather
from polars_baseball._config import (
    DEFAULT_GAMEFEED_CONCURRENCY_LIMIT,
    DEFAULT_STATCAST_CONCURRENCY_LIMIT,
    SAVANT_GAMEFEED_URL,
    SAVANT_INVALID_PLAYER_ID,
    SAVANT_ROOT,
    SAVANT_STATCAST_SEARCH_URL,
    STATCAST_DATE_STEP,
    STATCAST_FIRST_YEAR,
    STATCAST_PARK_FACTORS_START_YEAR,
)
from polars_baseball._leaderboard_registry import fetch_leaderboard
from polars_baseball._schemas.statcast import align_statcast_schemas
from polars_baseball._season import most_recent_season, sanitize_date_range, statcast_date_range
from polars_baseball.enums.pitch import norm_pitch_code
from polars_baseball.enums.position import pos_to_numeric
from polars_baseball.enums.savant import ArsenalType
from polars_baseball.exceptions import (
    InvalidParameterError,
    UpstreamParseError,
    UpstreamUnavailableError,
)
from polars_baseball.gateways.savant import SavantGateway
from polars_baseball.gateways.statcast_dataset import StatcastDatasetGateway
from polars_baseball.parsers.savant import parse_savant_park_factors
from polars_baseball.parsers.savant_gamefeed import (
    EXIT_VELOCITY_SCHEMA,
    PITCH_DATA_SCHEMA,
    SavantGamefeedParser,
)

if TYPE_CHECKING:
    from polars_baseball.client import BaseballClient

logger = logging.getLogger(__name__)

# Constants
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

PATH_PERCENTILE_RANKINGS = "/leaderboard/percentile-rankings"
PATH_PITCH_ARSENALS = "/leaderboard/pitch-arsenals"
PATH_PITCH_MOVEMENT = "/leaderboard/pitch-movement"
PATH_ACTIVE_SPIN = "/leaderboard/active-spin"
PATH_SPIN_COMP = "/leaderboard/spin-direction-comparison"
PATH_PARK_FACTORS = "/leaderboard/statcast-park-factors"

SAVANT_CSV_PARAM = "true"
SAVANT_MIN_QUALIFYING = "q"
SAVANT_DEFAULT_PITCH_TEMPO_MIN = 250
_ACTIVE_SPIN_TYPE_ORDER: tuple[str, ...] = ("spin-based", "observed")
_OAA_AGGREGATE_CODES = frozenset({"IF", "OF", "ALL", ""})
_EXIT_VELOCITY_DATASET = "exit_velocity"
_PITCH_DATA_DATASET = "pitch_data"

_BATTER_PROFILE_METRICS: tuple[tuple[str, str, str], ...] = (
    ("xwoba", "xwOBA", "rate"),
    ("xba", "xBA", "rate"),
    ("xslg", "xSLG", "rate"),
    ("xiso", "xISO", "rate"),
    ("xobp", "xOBP", "rate"),
    ("brl", "Barrels", "count"),
    ("brl_percent", "Barrel %", "pct"),
    ("exit_velocity", "Avg Exit Velo", "mph"),
    ("max_ev", "Max Exit Velo", "mph"),
    ("hard_hit_percent", "Hard-Hit %", "pct"),
    ("k_percent", "K %", "pct"),
    ("bb_percent", "BB %", "pct"),
    ("whiff_percent", "Whiff %", "pct"),
    ("chase_percent", "Chase %", "pct"),
    ("arm_strength", "Arm Strength", "mph"),
    ("sprint_speed", "Sprint Speed", "ft_s"),
    ("bat_speed", "Bat Speed", "mph"),
    ("squared_up_rate", "Squared-Up %", "pct"),
)

_PITCHER_PROFILE_METRICS: tuple[tuple[str, str, str], ...] = (
    ("xwoba", "xwOBA", "rate"),
    ("xba", "xBA", "rate"),
    ("xslg", "xSLG", "rate"),
    ("xiso", "xISO", "rate"),
    ("xobp", "xOBP", "rate"),
    ("brl", "Barrels", "count"),
    ("brl_percent", "Barrel %", "pct"),
    ("exit_velocity", "Avg Exit Velo", "mph"),
    ("max_ev", "Max Exit Velo", "mph"),
    ("hard_hit_percent", "Hard-Hit %", "pct"),
    ("k_percent", "K %", "pct"),
    ("bb_percent", "BB %", "pct"),
    ("whiff_percent", "Whiff %", "pct"),
    ("chase_percent", "Chase %", "pct"),
    ("arm_strength", "Arm Strength", "mph"),
    ("xera", "xERA", "rate"),
    ("fb_velocity", "Fastball Velo", "mph"),
    ("fb_spin", "Fastball Spin", "rpm"),
    ("curve_spin", "Curve Spin", "rpm"),
)

_EMPTY_PROFILE_SCHEMA: dict[str, pl.DataType | type[pl.DataType]] = {
    "metric": pl.String,
    "label": pl.String,
    "percentile": pl.Int64,
    "raw_value": pl.Float64,
    "unit": pl.String,
}


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


def _normalize_bat_side(bat_side: str) -> str:
    norm = str(bat_side).upper()
    if norm == "ALL":
        return "All"
    if norm in ("L", "R"):
        return norm
    raise InvalidParameterError("bat_side must be one of 'all', 'L', or 'R'.")


def _resolve_year_range(
    year: int | list[int] | tuple[int, int] | None,
    start_year: int | None,
    end_year: int | None,
) -> list[int]:
    if start_year is not None or end_year is not None:
        if start_year is None or end_year is None or not isinstance(start_year, int) or not isinstance(end_year, int):
            raise InvalidParameterError("Both start_year and end_year must be integers provided together.")
        if start_year > end_year:
            raise InvalidParameterError("start_year cannot be greater than end_year.")
        years = list(range(start_year, end_year + 1))
    elif isinstance(year, tuple):
        if len(year) != 2 or not isinstance(year[0], int) or not isinstance(year[1], int) or year[0] > year[1]:
            raise InvalidParameterError(
                "year tuple must be (start_year, end_year) with integer start_year <= end_year."
            )
        years = list(range(year[0], year[1] + 1))
    elif isinstance(year, list):
        if not year:
            raise InvalidParameterError("year list cannot be empty.")
        years = list(year)
    elif isinstance(year, int):
        years = [year]
    elif year is None:
        years = [most_recent_season()]
    else:
        raise InvalidParameterError(f"Invalid year specification: {year}")

    for yr in years:
        if not isinstance(yr, int) or yr < STATCAST_PARK_FACTORS_START_YEAR:
            raise InvalidParameterError(f"Year must be an integer >= {STATCAST_PARK_FACTORS_START_YEAR}.")
    return years


def _normalize_venue_ids(venue_id: int | list[int] | None) -> list[int] | None:
    if venue_id is None:
        return None
    if isinstance(venue_id, int):
        if venue_id <= 0:
            raise InvalidParameterError("venue_id must be a positive integer.")
        return [venue_id]
    if isinstance(venue_id, list):
        if not all(isinstance(v, int) and v > 0 for v in venue_id):
            raise InvalidParameterError("All venue_ids must be positive integers.")
        return list(venue_id)
    raise InvalidParameterError(f"Invalid venue_id specification: {type(venue_id).__name__}")


def _normalize_name_col(df: pl.DataFrame) -> pl.DataFrame:
    """Normalize 'last_name, first_name' to 'player_name' if needed."""
    if "last_name, first_name" in df.columns and "player_name" not in df.columns:
        return df.rename({"last_name, first_name": "player_name"})
    return df


async def _fetch_batter_raw_sources(client: BaseballClient, year: int) -> dict[str, pl.DataFrame]:
    """Fetch raw metric sources for batters concurrently."""
    sources: dict[str, pl.DataFrame] = {}

    async def _safe_call(fetcher: Callable[[], Awaitable[pl.DataFrame]]) -> pl.DataFrame:
        try:
            return await fetcher()
        except UpstreamUnavailableError:
            return pl.DataFrame()

    async def _fetch_exp() -> tuple[str, pl.DataFrame]:
        df = await _safe_call(lambda: client.savant.expected_stats(year, "batter"))
        return "exp", _normalize_name_col(df)

    async def _fetch_ev() -> tuple[str, pl.DataFrame]:
        df = await _safe_call(lambda: client.savant.exitvelo_barrels(year, "batter"))
        return "ev", _normalize_name_col(df)

    async def _fetch_sprint() -> tuple[str, pl.DataFrame]:
        df = await _safe_call(lambda: fetch_leaderboard("sprint_speed", client, year=str(year), min="1"))
        return "sprint", _normalize_name_col(df)

    tasks: list[Callable[[], Awaitable[tuple[str, pl.DataFrame]]]] = [_fetch_exp, _fetch_ev]
    if year >= 2015:
        tasks.append(_fetch_sprint)

    if year >= 2024:

        async def _fetch_bat() -> tuple[str, pl.DataFrame]:
            df = await _safe_call(lambda: client.savant.bat_tracking(year, "batter"))
            if "id" in df.columns and "player_id" not in df.columns:
                df = df.rename({"id": "player_id"})
            return "bat", _normalize_name_col(df)

        tasks.append(_fetch_bat)

    results = await bounded_gather(tasks, concurrency_limit=DEFAULT_STATCAST_CONCURRENCY_LIMIT)
    for key, data in results:
        sources[key] = data
    return sources


async def _fetch_pitcher_raw_sources(client: BaseballClient, year: int) -> dict[str, pl.DataFrame]:
    """Fetch raw metric sources for pitchers concurrently."""
    sources: dict[str, pl.DataFrame] = {}

    async def _safe_call(fetcher: Callable[[], Awaitable[pl.DataFrame]]) -> pl.DataFrame:
        try:
            return await fetcher()
        except UpstreamUnavailableError:
            return pl.DataFrame()

    async def _fetch_exp() -> tuple[str, pl.DataFrame]:
        df = await _safe_call(lambda: client.savant.pitcher_expected_stats(year))
        return "exp", _normalize_name_col(df)

    async def _fetch_ev() -> tuple[str, pl.DataFrame]:
        df = await _safe_call(lambda: client.savant.pitcher_exitvelo_barrels(year))
        return "ev", _normalize_name_col(df)

    async def _fetch_arsenal_speed() -> tuple[str, pl.DataFrame]:
        df = await _safe_call(
            lambda: client.savant.pitcher_pitch_arsenal(year, min_pitches=1, arsenal_type=ArsenalType.AVG_SPEED)
        )
        if "pitcher" in df.columns and "player_id" not in df.columns:
            df = df.rename({"pitcher": "player_id"})
        return "arsenal_speed", _normalize_name_col(df)

    async def _fetch_arsenal_spin() -> tuple[str, pl.DataFrame]:
        df = await _safe_call(
            lambda: client.savant.pitcher_pitch_arsenal(year, min_pitches=1, arsenal_type=ArsenalType.AVG_SPIN)
        )
        if "pitcher" in df.columns and "player_id" not in df.columns:
            df = df.rename({"pitcher": "player_id"})
        return "arsenal_spin", _normalize_name_col(df)

    tasks: list[Callable[[], Awaitable[tuple[str, pl.DataFrame]]]] = [
        _fetch_exp,
        _fetch_ev,
        _fetch_arsenal_speed,
        _fetch_arsenal_spin,
    ]
    results = await bounded_gather(tasks, concurrency_limit=DEFAULT_STATCAST_CONCURRENCY_LIMIT)
    for key, data in results:
        sources[key] = data
    return sources


def _extract_metric_series(df: pl.DataFrame, candidates: tuple[str, ...], target_name: str) -> pl.DataFrame:
    """Extract a player_id, target_name DataFrame from available candidate columns."""
    for col in candidates:
        if col in df.columns:
            return df.select(
                pl.col("player_id").cast(pl.Int64),
                pl.col(col).cast(pl.Float64, strict=False).alias(target_name),
            ).unique(subset=["player_id"])
    return pl.DataFrame(schema={"player_id": pl.Int64, target_name: pl.Float64})


def _collect_raw_metric_dfs(
    sources: dict[str, pl.DataFrame],
    is_batter: bool,
) -> list[pl.DataFrame]:
    """Collect metric Series DataFrames from raw data sources."""
    raw_dfs: list[pl.DataFrame] = []
    if "exp" in sources:
        exp_df = sources["exp"]
        raw_dfs.append(_extract_metric_series(exp_df, ("est_woba", "xwoba"), "xwoba_raw"))
        raw_dfs.append(_extract_metric_series(exp_df, ("est_ba", "xba"), "xba_raw"))
        raw_dfs.append(_extract_metric_series(exp_df, ("est_slg", "xslg"), "xslg_raw"))

    if "ev" in sources:
        ev_df = sources["ev"]
        raw_dfs.append(_extract_metric_series(ev_df, ("avg_hit_speed", "exit_velocity"), "exit_velocity_raw"))
        raw_dfs.append(_extract_metric_series(ev_df, ("max_hit_speed", "max_ev"), "max_ev_raw"))
        raw_dfs.append(_extract_metric_series(ev_df, ("ev95percent", "hard_hit_percent"), "hard_hit_percent_raw"))
        raw_dfs.append(_extract_metric_series(ev_df, ("barrels", "brl"), "brl_raw"))
        raw_dfs.append(_extract_metric_series(ev_df, ("brl_percent",), "brl_percent_raw"))

    if is_batter:
        if "bat" in sources:
            bat_df = sources["bat"]
            raw_dfs.append(_extract_metric_series(bat_df, ("avg_bat_speed", "bat_speed"), "bat_speed_raw"))
            raw_dfs.append(
                _extract_metric_series(bat_df, ("ideal_attack_angle_rate", "squared_up_rate"), "squared_up_rate_raw")
            )
        if "sprint" in sources:
            raw_dfs.append(_extract_metric_series(sources["sprint"], ("sprint_speed",), "sprint_speed_raw"))
    else:
        if "arsenal_speed" in sources:
            raw_dfs.append(_extract_metric_series(sources["arsenal_speed"], ("ff_avg_speed",), "fb_velocity_raw"))
        if "arsenal_spin" in sources:
            raw_dfs.append(_extract_metric_series(sources["arsenal_spin"], ("ff_avg_spin",), "fb_spin_raw"))
            raw_dfs.append(_extract_metric_series(sources["arsenal_spin"], ("cu_avg_spin",), "curve_spin_raw"))

    return [df for df in raw_dfs if df.height > 0]


def _build_composite_ranks(
    percentile_df: pl.DataFrame,
    sources: dict[str, pl.DataFrame],
    is_batter: bool,
) -> pl.DataFrame:
    """Left-join raw statistics onto percentile rankings DataFrame."""
    result = percentile_df.clone()
    if "player_id" in result.columns:
        result = result.with_columns(pl.col("player_id").cast(pl.Int64))

    profile_defs = _BATTER_PROFILE_METRICS if is_batter else _PITCHER_PROFILE_METRICS
    rename_map = {
        metric_name: f"{metric_name}_percentile" for metric_name, _, _ in profile_defs if metric_name in result.columns
    }
    result = result.rename(rename_map)

    cast_exprs = [pl.col(col).cast(pl.Int64, strict=False) for col in result.columns if col.endswith("_percentile")]
    if cast_exprs:
        result = result.with_columns(cast_exprs)

    for raw_df in _collect_raw_metric_dfs(sources, is_batter):
        result = result.join(raw_df, on="player_id", how="left")

    for metric_name, _, _ in profile_defs:
        raw_col = f"{metric_name}_raw"
        if raw_col not in result.columns:
            result = result.with_columns(pl.lit(None, dtype=pl.Float64).alias(raw_col))
        else:
            result = result.with_columns(pl.col(raw_col).cast(pl.Float64, strict=False))

    return result


class SavantClient:
    """Namespaced Baseball Savant and Statcast client."""

    def __init__(self, client: BaseballClient) -> None:
        self._client = client

    # -------------------------------------------------------------------------
    # Core Statcast Query Engine
    # -------------------------------------------------------------------------

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
        return await SavantGateway(self._client).get_dataset(
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
        return await SavantGateway(self._client).get_dataset(
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
        df = await SavantGateway(self._client).get_dataset(url)
        if df.is_empty():
            return pl.DataFrame()
        return _sort_statcast(df)

    statcast_single_game = single_game

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

    statcast_batter = batter

    async def pitcher(
        self,
        start_date: str | date | None = None,
        end_date: str | date | None = None,
        player_id: int | None = None,
    ) -> pl.DataFrame:
        """Fetch Statcast data for a specific pitcher."""
        return await self._statcast_player("pitcher", start_date, end_date, player_id)

    statcast_pitcher = pitcher

    # -------------------------------------------------------------------------
    # Compiled Statcast Dataset (scan + sync)
    # -------------------------------------------------------------------------

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

        gateway = StatcastDatasetGateway(self._client)
        paths: list[Path] = []
        for year in years:
            _validate_season(year)
            if gateway.year_exists(year) and not force_update:
                paths.append(gateway.partition_path(year))
                continue
            start = date(year, 1, 1)
            stop = date(year, 12, 31)
            date_range = list(statcast_date_range(start, stop, step=STATCAST_DATE_STEP, verbose=False))
            frames = await self._run_statcast_parallel(date_range, None, verbose, concurrency_limit)
            dfs = [df for df in frames if df is not None and not df.is_empty()]
            df = pl.concat(align_statcast_schemas(dfs), how="diagonal") if dfs else pl.DataFrame()
            paths.append(await gateway.write_partition(year, df))
        return paths

    async def scan_statcast(
        self,
        seasons: int | Sequence[int] | None = None,
        auto_download: bool = False,
    ) -> pl.LazyFrame:
        """Lazily scan the local Statcast Hive-partitioned Parquet dataset."""
        gateway = StatcastDatasetGateway(self._client)
        years = _normalize_seasons(seasons)
        if years is not None:
            for year in years:
                _validate_season(year)
            synced = set(gateway.synced_seasons())
            missing = [year for year in years if year not in synced]
            if missing:
                if auto_download:
                    await self.sync_statcast(missing)
                else:
                    raise UpstreamUnavailableError(
                        f"No local Statcast partition for season(s): {sorted(missing)}. "
                        "Run sync_statcast() or pass auto_download=True."
                    )
        return gateway.scan(years)

    # -------------------------------------------------------------------------
    # Gamefeed APIs
    # -------------------------------------------------------------------------

    async def gamefeed_exit_velocity(self, game_pk: int | str) -> pl.DataFrame:
        """Fetch exit velocity data for a single game."""
        parser = SavantGamefeedParser()
        return await SavantGateway(self._client).get_gamefeed_dataset(
            SAVANT_GAMEFEED_URL,
            _validate_game_pk(game_pk),
            _EXIT_VELOCITY_DATASET,
            parser.parse_exit_velocity,
        )

    async def gamefeed_pitch_data(self, game_pk: int | str) -> pl.DataFrame:
        """Fetch pitch-by-pitch data for a single game."""
        parser = SavantGamefeedParser()
        return await SavantGateway(self._client).get_gamefeed_dataset(
            SAVANT_GAMEFEED_URL,
            _validate_game_pk(game_pk),
            _PITCH_DATA_DATASET,
            parser.parse_pitch_data,
        )

    async def _fetch_many_gamefeed(
        self,
        game_pks: Sequence[int | str],
        single_fetcher: Callable[[int], Awaitable[pl.DataFrame]],
        empty_schema: Mapping[str, pl.DataType | type[pl.DataType]],
        parallel: bool = True,
        concurrency_limit: int = DEFAULT_GAMEFEED_CONCURRENCY_LIMIT,
    ) -> pl.DataFrame:
        if not game_pks:
            return pl.DataFrame(schema=empty_schema)
        validated = [_validate_game_pk(pk) for pk in game_pks]
        effective_limit = concurrency_limit if parallel else 1
        tasks = [lambda pk=pk: single_fetcher(pk) for pk in validated]
        dfs: list[pl.DataFrame] = await bounded_gather(tasks, concurrency_limit=effective_limit)
        return pl.concat(dfs, how="diagonal")

    async def gamefeed_exit_velocity_many(
        self,
        game_pks: Sequence[int | str],
        parallel: bool = True,
        concurrency_limit: int = DEFAULT_GAMEFEED_CONCURRENCY_LIMIT,
    ) -> pl.DataFrame:
        """Fetch exit velocity data for multiple games."""
        return await self._fetch_many_gamefeed(
            game_pks,
            self.gamefeed_exit_velocity,
            EXIT_VELOCITY_SCHEMA,
            parallel=parallel,
            concurrency_limit=concurrency_limit,
        )

    async def gamefeed_pitch_data_many(
        self,
        game_pks: Sequence[int | str],
        parallel: bool = True,
        concurrency_limit: int = DEFAULT_GAMEFEED_CONCURRENCY_LIMIT,
    ) -> pl.DataFrame:
        """Fetch pitch-by-pitch data for multiple games."""
        return await self._fetch_many_gamefeed(
            game_pks,
            self.gamefeed_pitch_data,
            PITCH_DATA_SCHEMA,
            parallel=parallel,
            concurrency_limit=concurrency_limit,
        )

    # -------------------------------------------------------------------------
    # Leaderboards
    # -------------------------------------------------------------------------

    async def _percentile_ranks_generic(
        self,
        player_type: Literal["batter", "pitcher"],
        year: int,
    ) -> pl.DataFrame:
        url = f"{SAVANT_ROOT}{PATH_PERCENTILE_RANKINGS}"
        params = {
            "type": player_type,
            "year": str(year),
            "position": "",
            "team": "",
            "csv": SAVANT_CSV_PARAM,
        }
        df = await SavantGateway(self._client).get_leaderboard(url, params)
        if df.height > 0:
            if "player_name" in df.columns:
                df = df.filter(pl.col("player_name").is_not_null() & (pl.col("player_name").str.strip_chars() != ""))
            if "player_id" in df.columns:
                df = df.filter(pl.col("player_id") != SAVANT_INVALID_PLAYER_ID)
        return df

    async def batter_percentile_ranks(self, year: int) -> pl.DataFrame:
        """Fetch Statcast percentile rankings for batters."""
        return await self._percentile_ranks_generic("batter", year)

    async def pitcher_percentile_ranks(self, year: int) -> pl.DataFrame:
        """Fetch Statcast percentile rankings for pitchers."""
        return await self._percentile_ranks_generic("pitcher", year)

    async def exitvelo_barrels(
        self,
        year: int,
        player_type: Literal["batter", "pitcher"] = "batter",
        min_bbe: int | str = SAVANT_MIN_QUALIFYING,
    ) -> pl.DataFrame:
        """Fetch exit velocity and barrel rate leaderboard data."""
        return await fetch_leaderboard(
            "exitvelo_barrels", self._client, type=player_type, year=str(year), min=str(min_bbe)
        )

    statcast_exitvelo_barrels = exitvelo_barrels

    async def pitcher_exitvelo_barrels(
        self,
        year: int,
        min_bbe: int | str = SAVANT_MIN_QUALIFYING,
    ) -> pl.DataFrame:
        """Fetch exit velocity and barrel rate leaderboard for pitchers."""
        return await self.exitvelo_barrels(year, "pitcher", min_bbe)

    statcast_pitcher_exitvelo_barrels = pitcher_exitvelo_barrels

    async def expected_stats(
        self,
        year: int,
        player_type: Literal["batter", "pitcher"] = "batter",
        min_pa: int | str = SAVANT_MIN_QUALIFYING,
    ) -> pl.DataFrame:
        """Fetch expected stats (xBA, xSLG, xwOBA) leaderboard."""
        return await fetch_leaderboard(
            "expected_stats", self._client, type=player_type, year=str(year), min=str(min_pa)
        )

    statcast_expected_stats = expected_stats

    async def pitcher_expected_stats(
        self,
        year: int,
        min_pa: int | str = SAVANT_MIN_QUALIFYING,
    ) -> pl.DataFrame:
        """Fetch expected stats leaderboard for pitchers."""
        return await self.expected_stats(year, "pitcher", min_pa)

    statcast_pitcher_expected_stats = pitcher_expected_stats

    async def pitch_arsenal_stats(
        self,
        year: int,
        min_pitches: int = 250,
        player_type: Literal["batter", "pitcher"] = "pitcher",
    ) -> pl.DataFrame:
        """Fetch pitch arsenal statistics leaderboard."""
        return await fetch_leaderboard(
            "pitch_arsenal_stats", self._client, type=player_type, year=str(year), min=str(min_pitches)
        )

    statcast_pitch_arsenal_stats = pitch_arsenal_stats

    async def pitcher_arsenal_stats(
        self,
        year: int,
        min_pitches: int = 250,
    ) -> pl.DataFrame:
        """Fetch pitch arsenal statistics for pitchers."""
        return await self.pitch_arsenal_stats(year, min_pitches, "pitcher")

    statcast_pitcher_arsenal_stats = pitcher_arsenal_stats

    async def pitcher_pitch_arsenal(
        self,
        year: int,
        min_pitches: int = 250,
        arsenal_type: ArsenalType = ArsenalType.AVG_SPEED,
    ) -> pl.DataFrame:
        """Fetch pitcher pitch arsenal metrics."""
        if not isinstance(arsenal_type, ArsenalType):
            raise InvalidParameterError("arsenal_type must be an ArsenalType enum value.")
        url = f"{SAVANT_ROOT}{PATH_PITCH_ARSENALS}"
        params = {
            "year": str(year),
            "min": str(min_pitches),
            "type": arsenal_type.value,
            "hand": "",
            "csv": SAVANT_CSV_PARAM,
        }
        return await SavantGateway(self._client).get_leaderboard(url, params)

    statcast_pitcher_pitch_arsenal = pitcher_pitch_arsenal

    async def pitcher_pitch_movement(
        self,
        year: int,
        min_pitches: int | str = SAVANT_MIN_QUALIFYING,
        pitch_type: str = "FF",
    ) -> pl.DataFrame:
        """Fetch pitch movement leaderboard data."""
        pitch_code = norm_pitch_code(pitch_type)
        url = f"{SAVANT_ROOT}{PATH_PITCH_MOVEMENT}"
        params = {
            "year": str(year),
            "team": "",
            "min": str(min_pitches),
            "pitch_type": pitch_code,
            "hand": "",
            "x": "pitcher_break_x_hidden",
            "z": "pitcher_break_z_hidden",
            "csv": SAVANT_CSV_PARAM,
        }
        return await SavantGateway(self._client).get_leaderboard(url, params)

    statcast_pitcher_pitch_movement = pitcher_pitch_movement

    async def pitcher_active_spin(
        self,
        year: int,
        min_pitches: int = 250,
    ) -> pl.DataFrame:
        """Fetch pitcher active spin leaderboard data."""
        gw = SavantGateway(self._client)
        url = f"{SAVANT_ROOT}{PATH_ACTIVE_SPIN}"

        for idx, spin_type in enumerate(_ACTIVE_SPIN_TYPE_ORDER):
            params = {"year": f"{year}_{spin_type}", "min": str(min_pitches), "hand": "", "csv": SAVANT_CSV_PARAM}
            df = await gw.get_optional_dataset(url, params)
            if df is not None:
                return df
            if idx == 0:
                warnings.warn(
                    f'Could not get active spin results for year {year} that are "spin-based". '
                    f'Trying to get the older "observed" results.',
                    stacklevel=2,
                )
        raise UpstreamParseError("Statcast did not return any active spin results for the query provided.")

    statcast_pitcher_active_spin = pitcher_active_spin

    async def pitcher_spin_dir_comp(
        self,
        year: int,
        pitch_a: str = "FF",
        pitch_b: str = "CH",
        min_pitches: int = 100,
        pitcher_pov: bool = True,
    ) -> pl.DataFrame:
        """Fetch pitcher spin direction comparison data."""
        code_a = norm_pitch_code(pitch_a, to_word=True)
        code_b = norm_pitch_code(pitch_b, to_word=True)
        pov = "Pit" if pitcher_pov else "Bat"
        url = f"{SAVANT_ROOT}{PATH_SPIN_COMP}"
        params = {
            "year": str(year),
            "type": f"{code_a} / {code_b}",
            "min": str(min_pitches),
            "team": "",
            "pov": pov,
            "sort": "11",
            "sortDir": "asc",
            "csv": SAVANT_CSV_PARAM,
        }
        return await SavantGateway(self._client).get_leaderboard(url, params)

    statcast_pitcher_spin_dir_comp = pitcher_spin_dir_comp

    async def pitch_tempo(
        self,
        year: int,
        min_pitches: int = SAVANT_DEFAULT_PITCH_TEMPO_MIN,
    ) -> pl.DataFrame:
        """Fetch pitch tempo leaderboard data."""
        return await fetch_leaderboard("pitch_tempo", self._client, year=str(year), min=str(min_pitches))

    statcast_pitch_tempo = pitch_tempo

    async def bat_tracking(
        self,
        year: int,
        player_type: Literal["batter", "pitcher"] = "batter",
        min_swings: int | str = SAVANT_MIN_QUALIFYING,
    ) -> pl.DataFrame:
        """Fetch bat tracking (swing path, attack angle) leaderboard data."""
        return await fetch_leaderboard(
            "bat_tracking",
            self._client,
            dateStart=f"{year}-01-01",
            dateEnd=f"{year}-12-31",
            minSwings=str(min_swings),
            type=player_type,
        )

    statcast_bat_tracking = bat_tracking

    async def pitcher_bat_tracking(
        self,
        year: int,
        min_swings: int | str = SAVANT_MIN_QUALIFYING,
    ) -> pl.DataFrame:
        """Fetch bat tracking data for pitchers."""
        return await self.bat_tracking(year, "pitcher", min_swings)

    statcast_pitcher_bat_tracking = pitcher_bat_tracking

    async def run_value(
        self,
        year: int,
        player_type: Literal["batter", "pitcher"] = "batter",
    ) -> pl.DataFrame:
        """Fetch run value leaderboard data."""
        group = "pitcher" if player_type == "pitcher" else "batter"
        return await fetch_leaderboard("run_value", self._client, year=str(year), group=group)

    statcast_run_value = run_value

    async def pitcher_run_value(self, year: int) -> pl.DataFrame:
        """Fetch run value leaderboard for pitchers."""
        return await self.run_value(year, "pitcher")

    statcast_pitcher_run_value = pitcher_run_value

    # -------------------------------------------------------------------------
    # Fielding & Running APIs
    # -------------------------------------------------------------------------

    async def sprint_speed(self, year: int, min_opp: int = 10) -> pl.DataFrame:
        """Fetch sprint speed leaderboard data."""
        return await fetch_leaderboard("sprint_speed", self._client, year=str(year), min=str(min_opp))

    statcast_sprint_speed = sprint_speed

    async def running_splits(self, year: int, min_opp: int = 5, raw_splits: bool = True) -> pl.DataFrame:
        """Fetch Statcast running splits data."""
        split_type = "raw" if raw_splits else "percent"
        return await fetch_leaderboard(
            "running_splits", self._client, type=split_type, year=str(year), min=str(min_opp)
        )

    statcast_running_splits = running_splits

    async def base_stealing(self, year: int, min_attempts: int | str = "q") -> pl.DataFrame:
        """Fetch base stealing leaderboard data."""
        return await fetch_leaderboard("base_stealing", self._client, year=str(year), min=str(min_attempts))

    statcast_base_stealing = base_stealing

    async def baserunning_run_value(self, year: int, min_opp: int = 5) -> pl.DataFrame:
        """Fetch baserunning run value leaderboard data."""
        return await fetch_leaderboard("baserunning_run_value", self._client, year=str(year), min=str(min_opp))

    statcast_baserunning_run_value = baserunning_run_value

    async def outs_above_average(
        self,
        year: int,
        pos: int | str,
        min_att: int | str = SAVANT_MIN_QUALIFYING,
        view: str = "Fielder",
    ) -> pl.DataFrame:
        """Fetch Statcast Outs Above Average (OAA) leaderboard data."""
        pos_code = pos_to_numeric(pos)
        if pos_code == "2":
            raise InvalidParameterError("This particular leaderboard does not include catchers!")
        if pos_code in _OAA_AGGREGATE_CODES:
            raise InvalidParameterError(
                f"outs_above_average requires a specific position (e.g. 'LF', 'CF', 'RF', '1B', '2B', '3B', 'SS'), "
                f"not an aggregate code '{pos}'."
            )
        return await fetch_leaderboard(
            "outs_above_average",
            self._client,
            type=view,
            startYear=str(year),
            endYear=str(year),
            min=str(min_att),
            pos=pos_code,
        )

    statcast_outs_above_average = outs_above_average

    async def outfield_directional_oaa(
        self,
        year: int,
        min_opp: int | str = SAVANT_MIN_QUALIFYING,
        min_attempts: int | str | None = None,
    ) -> pl.DataFrame:
        """Fetch directional Outs Above Average for outfielders."""
        attempts = min_attempts if min_attempts is not None else min_opp
        return await fetch_leaderboard("directional_oaa", self._client, year=str(year), min=str(attempts))

    statcast_outfield_directional_oaa = outfield_directional_oaa

    async def outfield_catch_prob(
        self,
        year: int,
        min_opp: int | str = SAVANT_MIN_QUALIFYING,
        min_opportunities: int | str | None = None,
    ) -> pl.DataFrame:
        """Fetch outfielder catch probability leaderboard data."""
        opp = min_opportunities if min_opportunities is not None else min_opp
        return await fetch_leaderboard("catch_probability", self._client, year=str(year), min=str(opp))

    statcast_outfield_catch_prob = outfield_catch_prob

    async def outfielder_jump(
        self,
        year: int,
        min_att: int | str = SAVANT_MIN_QUALIFYING,
        min_attempts: int | str | None = None,
    ) -> pl.DataFrame:
        """Fetch outfielder jump metric leaderboard data."""
        att = min_attempts if min_attempts is not None else min_att
        return await fetch_leaderboard("outfielder_jump", self._client, year=str(year), min=str(att))

    statcast_outfielder_jump = outfielder_jump

    async def catcher_poptime(
        self,
        year: int,
        min_2b_att: int = 5,
        min_3b_att: int = 0,
        min_attempts_2b: int | None = None,
        min_attempts_3b: int | None = None,
    ) -> pl.DataFrame:
        """Fetch catcher pop time leaderboard data."""
        att_2b = min_attempts_2b if min_attempts_2b is not None else min_2b_att
        att_3b = min_attempts_3b if min_attempts_3b is not None else min_3b_att
        return await fetch_leaderboard("poptime", self._client, year=str(year), min2b=str(att_2b), min3b=str(att_3b))

    statcast_catcher_poptime = catcher_poptime

    async def catcher_framing(
        self,
        year: int,
        min_called_p: int | str = SAVANT_MIN_QUALIFYING,
        min_called_pitches: int | str | None = None,
    ) -> pl.DataFrame:
        """Fetch catcher framing leaderboard data."""
        called_p = min_called_pitches if min_called_pitches is not None else min_called_p
        df = await fetch_leaderboard(
            "catcher_framing", self._client, seasonStart=str(year), seasonEnd=str(year), min=str(called_p)
        )
        if df.height > 0 and "name" in df.columns:
            df = df.filter(pl.col("name").is_not_null() & (pl.col("name").str.strip_chars() != ""))
        return df

    statcast_catcher_framing = catcher_framing

    async def catcher_blocking(self, year: int, min_chances: int = 100) -> pl.DataFrame:
        """Fetch catcher blocking leaderboard data."""
        return await fetch_leaderboard("catcher_blocking", self._client, year=str(year), min_chances=str(min_chances))

    statcast_catcher_blocking = catcher_blocking

    async def arm_strength(self, year: int, min_throws: int = 50) -> pl.DataFrame:
        """Fetch arm strength leaderboard data."""
        return await fetch_leaderboard("arm_strength", self._client, year=str(year), min=str(min_throws))

    statcast_arm_strength = arm_strength

    async def catcher_throwing(
        self,
        year: int,
        min_att: int = 5,
        min_attempts: int | None = None,
    ) -> pl.DataFrame:
        """Fetch catcher throwing run value leaderboard data."""
        att = min_attempts if min_attempts is not None else min_att
        return await fetch_leaderboard("catcher_throwing", self._client, year=str(year), min_att=str(att))

    statcast_catcher_throwing = catcher_throwing

    async def catcher_stance(self, year: int) -> pl.DataFrame:
        """Fetch catcher stance data."""
        return await fetch_leaderboard("catcher_stance", self._client, year=str(year))

    statcast_catcher_stance = catcher_stance

    async def fielding_run_value(
        self,
        year: int,
        position: int | str | None = None,
        pos: int | str | None = None,
        min_inn: int | None = None,
    ) -> pl.DataFrame:
        """Fetch fielding run value leaderboard data."""
        target_pos = position if position is not None else pos
        pos_str = "" if target_pos is None else pos_to_numeric(target_pos)
        min_str = "" if min_inn is None else str(min_inn)
        return await fetch_leaderboard(
            "fielding_run_value",
            self._client,
            seasonStart=str(year),
            seasonEnd=str(year),
            position=pos_str,
            minInnings=min_str,
        )

    statcast_fielding_run_value = fielding_run_value

    # -------------------------------------------------------------------------
    # Park Factors & Percentile Profiles
    # -------------------------------------------------------------------------

    async def park_factors(
        self,
        year: int | list[int] | tuple[int, int] | None = None,
        start_year: int | None = None,
        end_year: int | None = None,
        venue_id: int | list[int] | None = None,
        bat_side: Literal["all", "L", "R"] = "all",
        concurrency_limit: int = DEFAULT_STATCAST_CONCURRENCY_LIMIT,
    ) -> pl.DataFrame:
        """Fetch Statcast Park Factors from Baseball Savant."""
        savant_bat_side = _normalize_bat_side(bat_side)
        years = _resolve_year_range(year, start_year, end_year)
        venue_ids = _normalize_venue_ids(venue_id)

        async def _fetch_yr(yr: int) -> pl.DataFrame:
            url = f"{SAVANT_ROOT}{PATH_PARK_FACTORS}"
            params = {"type": "year", "year": str(yr), "batSide": savant_bat_side}
            raw = await SavantGateway(self._client).get_leaderboard(url, params)
            return parse_savant_park_factors(raw)

        tasks = [lambda yr=yr: _fetch_yr(yr) for yr in years]
        results = await bounded_gather(tasks, concurrency_limit=concurrency_limit)
        df = pl.concat(results, how="vertical") if results else pl.DataFrame()

        if venue_ids is not None and not df.is_empty():
            df = df.filter(pl.col("venue_id").is_in(venue_ids))
        return df

    savant_park_factors = park_factors

    async def composite_percentile_ranks(
        self,
        year: int,
        player_type: Literal["batter", "pitcher"] = "batter",
    ) -> pl.DataFrame:
        """Fetch Statcast percentile rankings combined with raw metric values."""
        if player_type not in ("batter", "pitcher"):
            raise InvalidParameterError(f"player_type must be 'batter' or 'pitcher', got {player_type!r}")

        pct_df = await self._percentile_ranks_generic(player_type, year)
        if pct_df.is_empty():
            return pct_df

        if player_type == "batter":
            sources = await _fetch_batter_raw_sources(self._client, year)
            return _build_composite_ranks(pct_df, sources, is_batter=True)
        sources = await _fetch_pitcher_raw_sources(self._client, year)
        return _build_composite_ranks(pct_df, sources, is_batter=False)

    statcast_composite_percentile_ranks = composite_percentile_ranks

    async def player_percentile_profile(
        self,
        player_id: int,
        year: int,
        player_type: Literal["batter", "pitcher"] | None = None,
    ) -> pl.DataFrame:
        """Fetch a single player's percentile ranks and raw metric values as a long-form profile."""
        empty_df = pl.DataFrame(schema=_EMPTY_PROFILE_SCHEMA)
        if player_type is not None:
            target_type: Literal["batter", "pitcher"] = player_type
            comp_df = await self.composite_percentile_ranks(year, player_type=target_type)
            player_row = comp_df.filter(pl.col("player_id") == player_id) if not comp_df.is_empty() else pl.DataFrame()
        else:
            target_type = "batter"
            comp_df = await self.composite_percentile_ranks(year, player_type="batter")
            player_row = comp_df.filter(pl.col("player_id") == player_id) if not comp_df.is_empty() else pl.DataFrame()
            if player_row.is_empty():
                target_type = "pitcher"
                comp_df = await self.composite_percentile_ranks(year, player_type="pitcher")
                player_row = (
                    comp_df.filter(pl.col("player_id") == player_id) if not comp_df.is_empty() else pl.DataFrame()
                )

        if player_row.is_empty():
            return empty_df

        defs = _BATTER_PROFILE_METRICS if target_type == "batter" else _PITCHER_PROFILE_METRICS
        row = player_row.to_dicts()[0]
        records = []
        for metric_name, label, unit in defs:
            pct_val = row.get(f"{metric_name}_percentile")
            raw_val = row.get(f"{metric_name}_raw")
            records.append(
                {
                    "metric": metric_name,
                    "label": label,
                    "percentile": int(pct_val) if pct_val is not None else None,
                    "raw_value": float(raw_val) if raw_val is not None else None,
                    "unit": unit,
                }
            )
        return pl.DataFrame(records, schema=_EMPTY_PROFILE_SCHEMA)

    statcast_player_percentile_profile = player_percentile_profile


def __getattr__(name: str) -> None:
    raise AttributeError(
        f"Top-level function 'polars_baseball.savant.{name}' was removed. "
        f"Use BaseballClient: `client = BaseballClient(); await client.savant.{name}(...)`."
    )


__all__ = ["SavantClient"]
