import warnings
from typing import Final, Literal, TypeVar

import polars as pl

from polars_baseball._config import SAVANT_INVALID_PLAYER_ID, SAVANT_ROOT
from polars_baseball.apis._leaderboard_registry import get_leaderboard
from polars_baseball.context import BaseballContext
from polars_baseball.enums.pitch import norm_pitch_code
from polars_baseball.enums.savant import ArsenalType
from polars_baseball.exceptions import InvalidParameterError, UpstreamParseError
from polars_baseball.gateways.savant import SavantGateway

# Savant leaderboard constants
SAVANT_CSV_PARAM = "true"
SAVANT_MIN_QUALIFYING = "q"

# Endpoint paths
PATH_PERCENTILE_RANKINGS = "/leaderboard/percentile-rankings"
PATH_PITCH_ARSENALS = "/leaderboard/pitch-arsenals"
PATH_PITCH_MOVEMENT = "/leaderboard/pitch-movement"
PATH_ACTIVE_SPIN = "/leaderboard/active-spin"
PATH_SPIN_COMP = "/leaderboard/spin-direction-comparison"

SAVANT_DEFAULT_PITCH_TEMPO_MIN = 250

# Version at which the deprecated legacy APIs and parameters are removed.
_REMOVAL_VERSION: Final[str] = "0.16.0"


def _warn_deprecated_param(old_name: str, new_name: str) -> None:
    warnings.warn(
        f"The `{old_name}` parameter is deprecated; use `{new_name}` instead. "
        f"It will be removed in v{_REMOVAL_VERSION}.",
        DeprecationWarning,
        stacklevel=3,
    )


def _warn_deprecated_function(old_name: str, replacement: str) -> None:
    """Warn that a function is deprecated and scheduled for removal."""
    warnings.warn(
        f"{old_name} is deprecated; use {replacement} instead. It will be removed in v{_REMOVAL_VERSION}.",
        DeprecationWarning,
        stacklevel=3,
    )


_MinParam = TypeVar("_MinParam")


def _resolve_min_alias(primary: _MinParam, old_name: str, new_name: str, legacy: _MinParam | None) -> _MinParam:
    if legacy is not None:
        _warn_deprecated_param(old_name, new_name)
        return legacy
    return primary


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
    minBBE: int | str | None = None,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch exit velocity and barrel rate leaderboard data."""
    min_bbe = _resolve_min_alias(min_bbe, "minBBE", "min_bbe", minBBE)
    return await get_leaderboard(
        "exitvelo_barrels", context=context, type=player_type, year=str(year), min=str(min_bbe)
    )


async def statcast_expected_stats(
    year: int,
    player_type: Literal["batter", "pitcher"] = "batter",
    min_pa: int | str = SAVANT_MIN_QUALIFYING,
    minPA: int | str | None = None,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch Statcast expected statistics (xBA, xSLG, xwOBA) leaderboard data."""
    min_pa = _resolve_min_alias(min_pa, "minPA", "min_pa", minPA)
    return await get_leaderboard("expected_stats", context=context, type=player_type, year=str(year), min=str(min_pa))


async def statcast_bat_tracking(
    year: int,
    player_type: Literal["batter", "pitcher"] = "batter",
    min_swings: int | str = SAVANT_MIN_QUALIFYING,
    minSwings: int | str | None = None,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch Statcast bat tracking (swing path, attack angle) leaderboard data."""
    min_swings = _resolve_min_alias(min_swings, "minSwings", "min_swings", minSwings)
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
    min_count: int | None = None,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch pitch arsenal usage and performance leaderboard data."""
    min_pitches = _resolve_min_alias(min_pitches, "min_count", "min_pitches", min_count)
    return await get_leaderboard(
        "pitch_arsenal_stats", context=context, type=player_type, year=str(year), min=str(min_pitches)
    )


# Legacy batter wrappers


async def statcast_batter_exitvelo_barrels(
    year: int,
    min_bbe: int | str = SAVANT_MIN_QUALIFYING,
    minBBE: int | str | None = None,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch exit velocity and barrel rate leaderboard for batters.

    Deprecated; use :func:`statcast_exitvelo_barrels` with ``player_type="batter"``.
    """
    _warn_deprecated_function(
        "statcast_batter_exitvelo_barrels",
        "statcast_exitvelo_barrels(year, player_type='batter', ...)",
    )
    min_bbe = _resolve_min_alias(min_bbe, "minBBE", "min_bbe", minBBE)
    return await statcast_exitvelo_barrels(year, "batter", min_bbe, context=context)


async def statcast_batter_expected_stats(
    year: int,
    min_pa: int | str = SAVANT_MIN_QUALIFYING,
    minPA: int | str | None = None,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch Statcast expected statistics (xBA, xSLG, xwOBA) for batters.

    Deprecated; use :func:`statcast_expected_stats` with ``player_type="batter"``.
    """
    _warn_deprecated_function(
        "statcast_batter_expected_stats",
        "statcast_expected_stats(year, player_type='batter', ...)",
    )
    min_pa = _resolve_min_alias(min_pa, "minPA", "min_pa", minPA)
    return await statcast_expected_stats(year, "batter", min_pa, context=context)


async def statcast_batter_percentile_ranks(
    year: int,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch Statcast percentile rankings for batters.

    Note: Filters out rows with null/empty player_name and invalid player_id.
    """
    return await _percentile_ranks_generic("batter", year, context=context)


async def statcast_batter_pitch_arsenal(
    year: int,
    min_pitches: int = 25,
    minPA: int | None = None,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch pitch arsenal stats for batters.

    Deprecated; use :func:`statcast_pitch_arsenal_stats` with ``player_type="batter"``.
    """
    _warn_deprecated_function(
        "statcast_batter_pitch_arsenal",
        "statcast_pitch_arsenal_stats(year, player_type='batter', ...)",
    )
    min_pitches = _resolve_min_alias(min_pitches, "minPA", "min_pitches", minPA)
    return await statcast_pitch_arsenal_stats(year, "batter", min_pitches, context=context)


async def statcast_batter_bat_tracking(
    year: int,
    min_swings: int | str = SAVANT_MIN_QUALIFYING,
    minSwings: int | str | None = None,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch bat tracking (swing path, attack angle) data for batters.

    Deprecated; use :func:`statcast_bat_tracking` with ``player_type="batter"``.
    """
    _warn_deprecated_function(
        "statcast_batter_bat_tracking",
        "statcast_bat_tracking(year, player_type='batter', ...)",
    )
    min_swings = _resolve_min_alias(min_swings, "minSwings", "min_swings", minSwings)
    return await statcast_bat_tracking(year, "batter", min_swings, context=context)


async def statcast_batter_run_value(
    year: int,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch run value leaderboard for batters.

    Deprecated; use :func:`statcast_run_value` with ``player_type="batter"``.
    """
    _warn_deprecated_function(
        "statcast_batter_run_value",
        "statcast_run_value(year, player_type='batter')",
    )
    return await statcast_run_value(year, "batter", context=context)


# Pitcher wrappers


async def statcast_pitcher_exitvelo_barrels(
    year: int,
    min_bbe: int | str = SAVANT_MIN_QUALIFYING,
    minBBE: int | str | None = None,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch exit velocity and barrel rate leaderboard for pitchers."""
    min_bbe = _resolve_min_alias(min_bbe, "minBBE", "min_bbe", minBBE)
    return await statcast_exitvelo_barrels(year, "pitcher", min_bbe, context=context)


async def statcast_pitcher_expected_stats(
    year: int,
    min_pa: int | str = SAVANT_MIN_QUALIFYING,
    minPA: int | str | None = None,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch Statcast expected statistics (xBA, xSLG, xwOBA) for pitchers."""
    min_pa = _resolve_min_alias(min_pa, "minPA", "min_pa", minPA)
    return await statcast_expected_stats(year, "pitcher", min_pa, context=context)


async def statcast_pitcher_pitch_arsenal(
    year: int,
    min_pitches: int = 250,
    minP: int | None = None,
    arsenal_type: ArsenalType = ArsenalType.AVG_SPEED,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch Statcast pitch arsenal data for pitchers.

    Note: arsenal_type must be an ArsenalType enum; raises InvalidParameterError otherwise.
    """
    if not isinstance(arsenal_type, ArsenalType):
        raise InvalidParameterError("arsenal_type must be an ArsenalType enum value.")
    min_pitches = _resolve_min_alias(min_pitches, "minP", "min_pitches", minP)
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
    minPA: int | None = None,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch pitch arsenal stats for pitchers."""
    min_pitches = _resolve_min_alias(min_pitches, "minPA", "min_pitches", minPA)
    return await statcast_pitch_arsenal_stats(year, "pitcher", min_pitches, context=context)


async def statcast_pitcher_pitch_movement(
    year: int,
    min_pitches: int | str = SAVANT_MIN_QUALIFYING,
    minP: int | str | None = None,
    pitch_type: str = "FF",
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch Statcast pitch movement data for a given pitch type.

    Note: pitch_type is normalized via norm_pitch_code; defaults to "FF" (four-seam fastball).
    """
    min_pitches = _resolve_min_alias(min_pitches, "minP", "min_pitches", minP)
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
    minP: int | None = None,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch Statcast active spin leaderboard data for pitchers.

    Note: Tries "spin-based" results first, falls back to "observed";
    raises UpstreamParseError if neither variant returns data.
    """
    min_pitches = _resolve_min_alias(min_pitches, "minP", "min_pitches", minP)
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


async def statcast_pitcher_spin_dir_comp(
    year: int,
    pitch_a: str = "FF",
    pitch_b: str = "CH",
    min_pitches: int = 100,
    minP: int | None = None,
    pitcher_pov: bool = True,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch Statcast spin direction comparison between two pitch types.

    Note: pitch_a and pitch_b are normalized via norm_pitch_code;
    pitcher_pov controls the perspective (True = Pitcher view, False = Batter view).
    """
    min_pitches = _resolve_min_alias(min_pitches, "minP", "min_pitches", minP)
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
    minSwings: int | str | None = None,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch bat tracking (swing path, attack angle) data for pitchers."""
    min_swings = _resolve_min_alias(min_swings, "minSwings", "min_swings", minSwings)
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
