import warnings
from typing import Literal

import polars as pl

from polars_baseball._config import SAVANT_INVALID_PLAYER_ID, SAVANT_ROOT
from polars_baseball.apis._leaderboard_registry import get_leaderboard
from polars_baseball.context import BaseballContext, default_context
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


async def _get_savant_leaderboard(
    url: str,
    params: dict[str, str] | None = None,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    ctx = context or default_context()
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
    minBBE: int | str = SAVANT_MIN_QUALIFYING,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch Statcast exit velocity and barrel rate leaderboard data."""
    return await get_leaderboard("exitvelo_barrels", context=context, type=player_type, year=str(year), min=str(minBBE))


async def statcast_expected_stats(
    year: int,
    player_type: Literal["batter", "pitcher"] = "batter",
    minPA: int | str = SAVANT_MIN_QUALIFYING,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch Statcast expected statistics (xBA, xSLG, xwOBA) leaderboard data."""
    return await get_leaderboard("expected_stats", context=context, type=player_type, year=str(year), min=str(minPA))


async def statcast_bat_tracking(
    year: int,
    player_type: Literal["batter", "pitcher"] = "batter",
    minSwings: int | str = SAVANT_MIN_QUALIFYING,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch Statcast bat tracking (swing path, attack angle) leaderboard data."""
    return await get_leaderboard(
        "bat_tracking",
        context=context,
        type=player_type,
        dateStart=f"{year}-01-01",
        dateEnd=f"{year}-12-31",
        minSwings=str(minSwings),
        seasonStart=str(year),
        seasonEnd=str(year),
    )


async def statcast_run_value(
    year: int,
    player_type: Literal["batter", "pitcher"] = "batter",
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch Statcast run value leaderboard data."""
    group = "Batter" if player_type == "batter" else "Pitcher"
    return await get_leaderboard("run_value", context=context, year=str(year), group=group)


async def statcast_pitch_arsenal_stats(
    year: int,
    player_type: Literal["batter", "pitcher"] = "batter",
    min_count: int = 25,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch Statcast pitch arsenal stats leaderboard data."""
    return await get_leaderboard(
        "pitch_arsenal_stats", context=context, type=player_type, year=str(year), min=str(min_count)
    )


# Legacy batter wrappers


async def statcast_batter_exitvelo_barrels(
    year: int,
    minBBE: int | str = SAVANT_MIN_QUALIFYING,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch Statcast exit velocity and barrel rate for batters."""
    return await statcast_exitvelo_barrels(year, "batter", minBBE, context=context)


async def statcast_batter_expected_stats(
    year: int,
    minPA: int | str = SAVANT_MIN_QUALIFYING,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch Statcast expected statistics (xBA, xSLG, xwOBA) for batters."""
    return await statcast_expected_stats(year, "batter", minPA, context=context)


async def statcast_batter_percentile_ranks(
    year: int,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch Statcast percentile rankings for batters.

    Edge Cases: Filters out rows with null/empty player_name and invalid player_id.
    """
    return await _percentile_ranks_generic("batter", year, context=context)


async def statcast_batter_pitch_arsenal(
    year: int,
    minPA: int = 25,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch Statcast pitch arsenal data for batters."""
    return await statcast_pitch_arsenal_stats(year, "batter", minPA, context=context)


async def statcast_batter_bat_tracking(
    year: int,
    minSwings: int | str = SAVANT_MIN_QUALIFYING,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch Statcast bat tracking data for batters."""
    return await statcast_bat_tracking(year, "batter", minSwings, context=context)


async def statcast_batter_run_value(
    year: int,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch Statcast run value data for batters."""
    return await statcast_run_value(year, "batter", context=context)


# Pitcher wrappers


async def statcast_pitcher_exitvelo_barrels(
    year: int,
    minBBE: int | str = SAVANT_MIN_QUALIFYING,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch Statcast exit velocity and barrel rate for pitchers."""
    return await statcast_exitvelo_barrels(year, "pitcher", minBBE, context=context)


async def statcast_pitcher_expected_stats(
    year: int,
    minPA: int | str = SAVANT_MIN_QUALIFYING,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch Statcast expected statistics (xBA, xSLG, xwOBA) for pitchers."""
    return await statcast_expected_stats(year, "pitcher", minPA, context=context)


async def statcast_pitcher_pitch_arsenal(
    year: int,
    minP: int = 250,
    arsenal_type: ArsenalType = ArsenalType.AVG_SPEED,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch Statcast pitch arsenal data for pitchers.

    Edge Cases: arsenal_type must be an ArsenalType enum; raises InvalidParameterError otherwise.
    """
    if not isinstance(arsenal_type, ArsenalType):
        raise InvalidParameterError("arsenal_type must be an ArsenalType enum value.")
    url = f"{SAVANT_ROOT}{PATH_PITCH_ARSENALS}"
    params = {
        "year": str(year),
        "min": str(minP),
        "type": arsenal_type.value,
        "hand": "",
        "csv": SAVANT_CSV_PARAM,
    }
    return await _get_savant_leaderboard(url, params, context=context)


async def statcast_pitcher_arsenal_stats(
    year: int,
    minPA: int = 25,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch Statcast pitcher arsenal stats leaderboard data."""
    return await statcast_pitch_arsenal_stats(year, "pitcher", minPA, context=context)


async def statcast_pitcher_pitch_movement(
    year: int,
    minP: int | str = SAVANT_MIN_QUALIFYING,
    pitch_type: str = "FF",
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch Statcast pitch movement data for a given pitch type.

    Edge Cases: pitch_type is normalized via norm_pitch_code; defaults to "FF" (four-seam fastball).
    """
    pitch_code = norm_pitch_code(pitch_type)
    url = f"{SAVANT_ROOT}{PATH_PITCH_MOVEMENT}"
    params = {
        "year": str(year),
        "team": "",
        "min": str(minP),
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
    ctx = context or default_context()
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
    minP: int = 250,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch Statcast active spin leaderboard data for pitchers.

    Edge Cases: Tries "spin-based" results first, falls back to "observed";
    raises UpstreamParseError if neither variant returns data.
    """
    for idx, spin_type in enumerate(_ACTIVE_SPIN_TYPE_ORDER):
        df = await _try_fetch_active_spin(year, minP, spin_type, context=context)
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

    Edge Cases: Filters out rows with null/empty player_name and invalid player_id.
    """
    return await _percentile_ranks_generic("pitcher", year, context=context)


async def statcast_pitcher_spin_dir_comp(
    year: int,
    pitch_a: str = "FF",
    pitch_b: str = "CH",
    minP: int = 100,
    pitcher_pov: bool = True,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch Statcast spin direction comparison between two pitch types.

    Edge Cases: pitch_a and pitch_b are normalized via norm_pitch_code;
    pitcher_pov controls the perspective (True = Pitcher view, False = Batter view).
    """
    code_a = norm_pitch_code(pitch_a, to_word=True)
    code_b = norm_pitch_code(pitch_b, to_word=True)
    pov = "Pit" if pitcher_pov else "Bat"
    url = f"{SAVANT_ROOT}{PATH_SPIN_COMP}"
    params = {
        "year": str(year),
        "type": f"{code_a} / {code_b}",
        "min": str(minP),
        "team": "",
        "pov": pov,
        "sort": "11",
        "sortDir": "asc",
        "csv": SAVANT_CSV_PARAM,
    }
    return await _get_savant_leaderboard(url, params, context=context)


async def statcast_pitcher_bat_tracking(
    year: int,
    minSwings: int | str = SAVANT_MIN_QUALIFYING,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch Statcast bat tracking data for pitchers."""
    return await statcast_bat_tracking(year, "pitcher", minSwings, context=context)


async def statcast_pitcher_run_value(
    year: int,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch Statcast run value data for pitchers."""
    return await statcast_run_value(year, "pitcher", context=context)


async def statcast_pitch_tempo(
    year: int,
    min_pitches: int = SAVANT_DEFAULT_PITCH_TEMPO_MIN,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch Statcast pitch tempo leaderboard data."""
    return await get_leaderboard("pitch_tempo", context=context, year=str(year), min=str(min_pitches))
