import asyncio
import warnings
from typing import Literal

import polars as pl

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
from polars_baseball.exceptions import InvalidParameterError, UpstreamParseError
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
) -> pl.DataFrame:
    """Fetch Statcast Park Factors from Baseball Savant.

    Args:
        year: Single year (int), list of years, or tuple (start_year, end_year).
        start_year: Start year for range query.
        end_year: End year for range query.
        venue_id: Single MLB venue ID or list of venue IDs to filter.
        bat_side: Batter side filter ('all', 'L', or 'R').
        context: Optional BaseballContext.

    Returns:
        DataFrame containing normalized Statcast Park Factors.
    """
    savant_bat_side = _normalize_bat_side(bat_side)
    years = _resolve_year_range(year, start_year, end_year)
    venue_ids = _normalize_venue_ids(venue_id)

    if len(years) == 1:
        df = await _fetch_savant_park_factors(
            year=years[0],
            bat_side=savant_bat_side,
            context=context,
        )
    else:
        sem = asyncio.Semaphore(DEFAULT_STATCAST_CONCURRENCY_LIMIT)

        async def _fetch_sem(yr: int) -> pl.DataFrame:
            async with sem:
                return await _fetch_savant_park_factors(
                    year=yr,
                    bat_side=savant_bat_side,
                    context=context,
                )

        results = await asyncio.gather(*[_fetch_sem(yr) for yr in years])
        df = pl.concat(results, how="vertical") if results else pl.DataFrame()

    if venue_ids is not None and not df.is_empty():
        df = df.filter(pl.col("venue_id").is_in(venue_ids))

    return df
