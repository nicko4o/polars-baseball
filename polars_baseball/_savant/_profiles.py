"""Baseball Savant composite percentile ranks and player profiles mixin."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import TYPE_CHECKING, Literal

import polars as pl

from polars_baseball._concurrency import bounded_gather
from polars_baseball._config import DEFAULT_STATCAST_CONCURRENCY_LIMIT
from polars_baseball._leaderboard_registry import fetch_leaderboard
from polars_baseball._savant._leaderboards import SavantLeaderboardMixin
from polars_baseball.enums.savant import ArsenalType
from polars_baseball.exceptions import (
    InvalidParameterError,
    UpstreamUnavailableError,
)

if TYPE_CHECKING:
    from polars_baseball.client import BaseballClient

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

    raw_col_exprs = [
        pl.lit(None, dtype=pl.Float64).alias(f"{metric_name}_raw")
        if f"{metric_name}_raw" not in result.columns
        else pl.col(f"{metric_name}_raw").cast(pl.Float64, strict=False)
        for metric_name, _, _ in profile_defs
    ]
    if raw_col_exprs:
        result = result.with_columns(raw_col_exprs)

    return result


class SavantProfilesMixin(SavantLeaderboardMixin):
    """Methods for Statcast player profiles and composite percentile ranks."""

    _client: BaseballClient

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
