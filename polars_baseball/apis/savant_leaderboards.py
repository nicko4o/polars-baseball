import warnings
from collections.abc import Awaitable, Callable
from typing import Literal

import polars as pl

from polars_baseball._concurrency import bounded_gather
from polars_baseball._config import (
    DEFAULT_STATCAST_CONCURRENCY_LIMIT,
    SAVANT_INVALID_PLAYER_ID,
    SAVANT_ROOT,
    STATCAST_PARK_FACTORS_START_YEAR,
)
from polars_baseball._season import most_recent_season
from polars_baseball.apis._leaderboard_registry import get_leaderboard
from polars_baseball.context import BaseballContext
from polars_baseball.enums.pitch import norm_pitch_code
from polars_baseball.enums.savant import ArsenalType
from polars_baseball.exceptions import (
    InvalidParameterError,
    UpstreamParseError,
    UpstreamUnavailableError,
)
from polars_baseball.gateways.savant import SavantGateway
from polars_baseball.parsers.savant import parse_savant_park_factors

# Savant leaderboard constants
SAVANT_CSV_PARAM = "true"
SAVANT_MIN_QUALIFYING = "q"

# Endpoint paths
PATH_PERCENTILE_RANKINGS = "/leaderboard/percentile-rankings"
PATH_PITCH_ARSENALS = "/leaderboard/pitch-arsenals"
PATH_PITCH_MOVEMENT = "/leaderboard/pitch-movement"
PATH_ACTIVE_SPIN = "/leaderboard/active-spin"
PATH_SPIN_COMP = "/leaderboard/spin-direction-comparison"
PATH_PARK_FACTORS = "/leaderboard/statcast-park-factors"

SAVANT_DEFAULT_PITCH_TEMPO_MIN = 250


async def _get_savant_leaderboard(
    url: str,
    params: dict[str, str] | None = None,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    ctx = context or BaseballContext.default()
    return await SavantGateway(ctx).get_leaderboard(url, params)


async def _percentile_ranks_generic(
    player_type: Literal["batter", "pitcher"],
    year: int,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    url = f"{SAVANT_ROOT}{PATH_PERCENTILE_RANKINGS}"
    params = {
        "type": player_type,
        "year": str(year),
        "position": "",
        "team": "",
        "csv": SAVANT_CSV_PARAM,
    }
    df = await _get_savant_leaderboard(url, params, context=context)
    if df.height > 0:
        if "player_name" in df.columns:
            df = df.filter(pl.col("player_name").is_not_null() & (pl.col("player_name").str.strip_chars() != ""))
        if "player_id" in df.columns:
            df = df.filter(pl.col("player_id") != SAVANT_INVALID_PLAYER_ID)
    return df


# Unified batter and pitcher APIs


async def statcast_exitvelo_barrels(
    year: int,
    player_type: Literal["batter", "pitcher"] = "batter",
    min_bbe: int | str = SAVANT_MIN_QUALIFYING,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch exit velocity and barrel rate leaderboard data."""
    return await get_leaderboard(
        "exitvelo_barrels", context=context, type=player_type, year=str(year), min=str(min_bbe)
    )


async def statcast_expected_stats(
    year: int,
    player_type: Literal["batter", "pitcher"] = "batter",
    min_pa: int | str = SAVANT_MIN_QUALIFYING,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch Statcast expected statistics (xBA, xSLG, xwOBA) leaderboard data."""
    return await get_leaderboard("expected_stats", context=context, type=player_type, year=str(year), min=str(min_pa))


async def statcast_bat_tracking(
    year: int,
    player_type: Literal["batter", "pitcher"] = "batter",
    min_swings: int | str = SAVANT_MIN_QUALIFYING,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch Statcast bat tracking (swing path, attack angle) leaderboard data."""
    return await get_leaderboard(
        "bat_tracking",
        context=context,
        type=player_type,
        dateStart=f"{year}-01-01",
        dateEnd=f"{year}-12-31",
        minSwings=str(min_swings),
        seasonStart=str(year),
        seasonEnd=str(year),
    )


async def statcast_run_value(
    year: int,
    player_type: Literal["batter", "pitcher"] = "batter",
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch run value (run expectancy) leaderboard data."""
    group = "Batter" if player_type == "batter" else "Pitcher"
    return await get_leaderboard("run_value", context=context, year=str(year), group=group)


async def statcast_pitch_arsenal_stats(
    year: int,
    player_type: Literal["batter", "pitcher"] = "batter",
    min_pitches: int = 25,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch pitch arsenal usage and performance leaderboard data."""
    return await get_leaderboard(
        "pitch_arsenal_stats", context=context, type=player_type, year=str(year), min=str(min_pitches)
    )


async def statcast_batter_percentile_ranks(
    year: int,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch Statcast percentile rankings for batters.

    Note: Filters out rows with null/empty player_name and invalid player_id.
    """
    return await _percentile_ranks_generic("batter", year, context=context)


# Pitcher wrappers


async def statcast_pitcher_exitvelo_barrels(
    year: int,
    min_bbe: int | str = SAVANT_MIN_QUALIFYING,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch exit velocity and barrel rate leaderboard for pitchers."""
    return await statcast_exitvelo_barrels(year, "pitcher", min_bbe, context=context)


async def statcast_pitcher_expected_stats(
    year: int,
    min_pa: int | str = SAVANT_MIN_QUALIFYING,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch Statcast expected statistics (xBA, xSLG, xwOBA) for pitchers."""
    return await statcast_expected_stats(year, "pitcher", min_pa, context=context)


async def statcast_pitcher_pitch_arsenal(
    year: int,
    min_pitches: int = 250,
    arsenal_type: ArsenalType = ArsenalType.AVG_SPEED,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch Statcast pitch arsenal data for pitchers.

    Note: arsenal_type must be an ArsenalType enum; raises InvalidParameterError otherwise.
    """
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
    return await _get_savant_leaderboard(url, params, context=context)


async def statcast_pitcher_arsenal_stats(
    year: int,
    min_pitches: int = 25,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch pitch arsenal stats for pitchers."""
    return await statcast_pitch_arsenal_stats(year, "pitcher", min_pitches, context=context)


async def statcast_pitcher_pitch_movement(
    year: int,
    min_pitches: int | str = SAVANT_MIN_QUALIFYING,
    pitch_type: str = "FF",
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch Statcast pitch movement data for a given pitch type.

    Note: pitch_type is normalized via norm_pitch_code; defaults to "FF" (four-seam fastball).
    """
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
    return await _get_savant_leaderboard(url, params, context=context)


_ACTIVE_SPIN_TYPE_ORDER: tuple[str, ...] = ("spin-based", "observed")


async def _try_fetch_active_spin(
    year: int,
    minP: int,
    spin_type: str,
    context: BaseballContext | None = None,
) -> pl.DataFrame | None:
    ctx = context or BaseballContext.default()
    url = f"{SAVANT_ROOT}{PATH_ACTIVE_SPIN}"
    params = {
        "year": f"{year}_{spin_type}",
        "min": str(minP),
        "hand": "",
        "csv": SAVANT_CSV_PARAM,
    }
    return await SavantGateway(ctx).get_optional_dataset(url, params)


async def statcast_pitcher_active_spin(
    year: int,
    min_pitches: int = 250,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch Statcast active spin leaderboard data for pitchers.

    Note: Tries "spin-based" results first, falls back to "observed";
    raises UpstreamParseError if neither variant returns data.
    """
    for idx, spin_type in enumerate(_ACTIVE_SPIN_TYPE_ORDER):
        df = await _try_fetch_active_spin(year, min_pitches, spin_type, context=context)
        if df is not None:
            return df
        if idx == 0:
            warnings.warn(
                f'Could not get active spin results for year {year} that are "spin-based". '
                f'Trying to get the older "observed" results.',
                stacklevel=2,
            )
    raise UpstreamParseError("Statcast did not return any active spin results for the query provided.")


async def statcast_pitcher_percentile_ranks(
    year: int,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch Statcast percentile rankings for pitchers.

    Note: Filters out rows with null/empty player_name and invalid player_id.
    """
    return await _percentile_ranks_generic("pitcher", year, context=context)


# Metric definitions: (metric_id, display_label, unit)
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


def _normalize_name_col(df: pl.DataFrame) -> pl.DataFrame:
    """Normalize 'last_name, first_name' to 'player_name' if needed."""
    if "last_name, first_name" in df.columns and "player_name" not in df.columns:
        return df.rename({"last_name, first_name": "player_name"})
    return df


async def _fetch_batter_raw_sources(year: int, context: BaseballContext | None) -> dict[str, pl.DataFrame]:
    """Fetch raw metric sources for batters concurrently."""
    sources: dict[str, pl.DataFrame] = {}

    async def _safe_call(fetcher: Callable[[], Awaitable[pl.DataFrame]]) -> pl.DataFrame:
        try:
            return await fetcher()
        except UpstreamUnavailableError:
            return pl.DataFrame()

    async def _fetch_exp() -> tuple[str, pl.DataFrame]:
        df = await _safe_call(lambda: statcast_expected_stats(year, "batter", context=context))
        return "exp", _normalize_name_col(df)

    async def _fetch_ev() -> tuple[str, pl.DataFrame]:
        df = await _safe_call(lambda: statcast_exitvelo_barrels(year, "batter", context=context))
        return "ev", _normalize_name_col(df)

    async def _fetch_sprint() -> tuple[str, pl.DataFrame]:
        df = await _safe_call(lambda: get_leaderboard("sprint_speed", context=context, year=str(year), min="1"))
        return "sprint", _normalize_name_col(df)

    tasks: list[Callable[[], Awaitable[tuple[str, pl.DataFrame]]]] = [_fetch_exp, _fetch_ev]
    if year >= 2015:
        tasks.append(_fetch_sprint)

    if year >= 2024:

        async def _fetch_bat() -> tuple[str, pl.DataFrame]:
            df = await _safe_call(lambda: statcast_bat_tracking(year, "batter", context=context))
            if "id" in df.columns and "player_id" not in df.columns:
                df = df.rename({"id": "player_id"})
            return "bat", _normalize_name_col(df)

        tasks.append(_fetch_bat)

    results = await bounded_gather(tasks, concurrency_limit=DEFAULT_STATCAST_CONCURRENCY_LIMIT)
    for key, data in results:
        sources[key] = data
    return sources


async def _fetch_pitcher_raw_sources(year: int, context: BaseballContext | None) -> dict[str, pl.DataFrame]:
    """Fetch raw metric sources for pitchers concurrently."""
    sources: dict[str, pl.DataFrame] = {}

    async def _safe_call(fetcher: Callable[[], Awaitable[pl.DataFrame]]) -> pl.DataFrame:
        try:
            return await fetcher()
        except UpstreamUnavailableError:
            return pl.DataFrame()

    async def _fetch_exp() -> tuple[str, pl.DataFrame]:
        df = await _safe_call(lambda: statcast_pitcher_expected_stats(year, context=context))
        return "exp", _normalize_name_col(df)

    async def _fetch_ev() -> tuple[str, pl.DataFrame]:
        df = await _safe_call(lambda: statcast_pitcher_exitvelo_barrels(year, context=context))
        return "ev", _normalize_name_col(df)

    async def _fetch_arsenal_speed() -> tuple[str, pl.DataFrame]:
        df = await _safe_call(
            lambda: statcast_pitcher_pitch_arsenal(
                year, min_pitches=1, arsenal_type=ArsenalType.AVG_SPEED, context=context
            )
        )
        if "pitcher" in df.columns and "player_id" not in df.columns:
            df = df.rename({"pitcher": "player_id"})
        return "arsenal_speed", _normalize_name_col(df)

    async def _fetch_arsenal_spin() -> tuple[str, pl.DataFrame]:
        df = await _safe_call(
            lambda: statcast_pitcher_pitch_arsenal(
                year, min_pitches=1, arsenal_type=ArsenalType.AVG_SPIN, context=context
            )
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


async def statcast_composite_percentile_ranks(
    year: int,
    player_type: Literal["batter", "pitcher"] = "batter",
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch Statcast percentile rankings combined with raw metric values.

    Args:
        year: Season year.
        player_type: 'batter' or 'pitcher'.
        context: Optional BaseballContext.

    Returns:
        Wide DataFrame with {metric}_percentile and {metric}_raw columns.
    """
    if player_type not in ("batter", "pitcher"):
        raise InvalidParameterError(f"player_type must be 'batter' or 'pitcher', got {player_type!r}")

    pct_df = await _percentile_ranks_generic(player_type, year, context=context)
    if pct_df.is_empty():
        return pct_df

    if player_type == "batter":
        sources = await _fetch_batter_raw_sources(year, context)
        return _build_composite_ranks(pct_df, sources, is_batter=True)
    sources = await _fetch_pitcher_raw_sources(year, context)
    return _build_composite_ranks(pct_df, sources, is_batter=False)


_EMPTY_PROFILE_SCHEMA: dict[str, pl.DataType | type[pl.DataType]] = {
    "metric": pl.String,
    "label": pl.String,
    "percentile": pl.Int64,
    "raw_value": pl.Float64,
    "unit": pl.String,
}


async def statcast_player_percentile_profile(
    player_id: int,
    year: int,
    player_type: Literal["batter", "pitcher"] | None = None,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch a single player's percentile ranks and raw metric values as a long-form profile.

    For two-way players (e.g. Shohei Ohtani), passing player_type=None defaults to batter profile;
    pass player_type='pitcher' to inspect pitching profile.

    Args:
        player_id: MLB player ID.
        year: Season year.
        player_type: 'batter', 'pitcher', or None (tries batter first, falls back to pitcher).
        context: Optional BaseballContext.

    Returns:
        Long DataFrame with columns [metric, label, percentile, raw_value, unit].
        Returns an empty DataFrame (0 rows) if no records found for the player.
    """
    empty_df = pl.DataFrame(schema=_EMPTY_PROFILE_SCHEMA)

    if player_type is not None:
        target_type = player_type
        comp_df = await statcast_composite_percentile_ranks(year, player_type=target_type, context=context)
        player_row = comp_df.filter(pl.col("player_id") == player_id) if not comp_df.is_empty() else pl.DataFrame()
    else:
        target_type = "batter"
        comp_df = await statcast_composite_percentile_ranks(year, player_type="batter", context=context)
        player_row = comp_df.filter(pl.col("player_id") == player_id) if not comp_df.is_empty() else pl.DataFrame()
        if player_row.is_empty():
            target_type = "pitcher"
            comp_df = await statcast_composite_percentile_ranks(year, player_type="pitcher", context=context)
            player_row = comp_df.filter(pl.col("player_id") == player_id) if not comp_df.is_empty() else pl.DataFrame()

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


async def statcast_pitcher_spin_dir_comp(
    year: int,
    pitch_a: str = "FF",
    pitch_b: str = "CH",
    min_pitches: int = 100,
    pitcher_pov: bool = True,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch Statcast spin direction comparison between two pitch types.

    Note: pitch_a and pitch_b are normalized via norm_pitch_code;
    pitcher_pov controls the perspective (True = Pitcher view, False = Batter view).
    """
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
    return await _get_savant_leaderboard(url, params, context=context)


async def statcast_pitcher_bat_tracking(
    year: int,
    min_swings: int | str = SAVANT_MIN_QUALIFYING,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch bat tracking (swing path, attack angle) data for pitchers."""
    return await statcast_bat_tracking(year, "pitcher", min_swings, context=context)


async def statcast_pitcher_run_value(
    year: int,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch run value leaderboard for pitchers."""
    return await statcast_run_value(year, "pitcher", context=context)


async def statcast_pitch_tempo(
    year: int,
    min_pitches: int = SAVANT_DEFAULT_PITCH_TEMPO_MIN,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch pitch tempo (pace-of-game) leaderboard data."""
    return await get_leaderboard("pitch_tempo", context=context, year=str(year), min=str(min_pitches))


async def _fetch_savant_park_factors(
    year: int,
    bat_side: str = "All",
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    url = f"{SAVANT_ROOT}{PATH_PARK_FACTORS}"
    params = {
        "type": "year",
        "year": str(year),
        "batSide": bat_side,
    }
    raw_df = await _get_savant_leaderboard(url, params, context=context)
    return parse_savant_park_factors(raw_df)


def _normalize_bat_side(bat_side: str) -> str:
    norm = str(bat_side).upper()
    if norm == "ALL":
        return "All"
    if norm in ("L", "R"):
        return norm
    raise InvalidParameterError("bat_side must be one of 'all', 'L', or 'R'.")


def _extract_years_list(
    year: int | list[int] | tuple[int, int] | None,
    start_year: int | None,
    end_year: int | None,
) -> list[int]:
    if start_year is not None or end_year is not None:
        if start_year is None or end_year is None or not isinstance(start_year, int) or not isinstance(end_year, int):
            raise InvalidParameterError("Both start_year and end_year must be integers provided together.")
        if start_year > end_year:
            raise InvalidParameterError("start_year cannot be greater than end_year.")
        return list(range(start_year, end_year + 1))

    if isinstance(year, tuple):
        if len(year) != 2 or not isinstance(year[0], int) or not isinstance(year[1], int) or year[0] > year[1]:
            raise InvalidParameterError(
                "year tuple must be (start_year, end_year) with integer start_year <= end_year."
            )
        return list(range(year[0], year[1] + 1))

    if isinstance(year, list):
        if not year:
            raise InvalidParameterError("year list cannot be empty.")
        return list(year)

    if isinstance(year, int):
        return [year]

    if year is None:
        return [most_recent_season()]

    raise InvalidParameterError(f"Invalid year specification: {year}")


def _resolve_year_range(
    year: int | list[int] | tuple[int, int] | None,
    start_year: int | None,
    end_year: int | None,
) -> list[int]:
    years = _extract_years_list(year, start_year, end_year)
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


async def savant_park_factors(
    year: int | list[int] | tuple[int, int] | None = None,
    start_year: int | None = None,
    end_year: int | None = None,
    venue_id: int | list[int] | None = None,
    bat_side: Literal["all", "L", "R"] = "all",
    context: BaseballContext | None = None,
    *,
    concurrency_limit: int = DEFAULT_STATCAST_CONCURRENCY_LIMIT,
) -> pl.DataFrame:
    """Fetch Statcast Park Factors from Baseball Savant.

    Args:
        year: Single year (int), list of years, or tuple (start_year, end_year).
        start_year: Start year for range query.
        end_year: End year for range query.
        venue_id: Single MLB venue ID or list of venue IDs to filter.
        bat_side: Batter side filter ('all', 'L', or 'R').
        context: Optional BaseballContext.
        concurrency_limit: Maximum concurrent requests when fetching multiple years.

    Returns:
        DataFrame containing normalized Statcast Park Factors.
    """
    savant_bat_side = _normalize_bat_side(bat_side)
    years = _resolve_year_range(year, start_year, end_year)
    venue_ids = _normalize_venue_ids(venue_id)

    tasks = [
        lambda yr=yr: _fetch_savant_park_factors(
            year=yr,
            bat_side=savant_bat_side,
            context=context,
        )
        for yr in years
    ]
    results = await bounded_gather(tasks, concurrency_limit=concurrency_limit)
    df = pl.concat(results, how="vertical") if results else pl.DataFrame()

    if venue_ids is not None and not df.is_empty():
        df = df.filter(pl.col("venue_id").is_in(venue_ids))

    return df
