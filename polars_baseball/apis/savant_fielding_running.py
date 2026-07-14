import polars as pl

from polars_baseball.apis._leaderboard_registry import get_leaderboard
from polars_baseball.apis.savant_leaderboards import SAVANT_MIN_QUALIFYING
from polars_baseball.context import BaseballContext
from polars_baseball.enums.position import pos_to_numeric
from polars_baseball.exceptions import InvalidParameterError

SAVANT_DEFAULT_CATCHER_BLOCKING_MIN = 100
SAVANT_DEFAULT_ARM_STRENGTH_MIN = 50
SAVANT_DEFAULT_BASERUNNING_MIN = 5
SAVANT_DEFAULT_CATCHER_THROWING_MIN = 5


# Running APIs


async def statcast_sprint_speed(
    year: int,
    min_opp: int = 10,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch Statcast sprint speed leaderboard data."""
    return await get_leaderboard("sprint_speed", context=context, year=str(year), min=str(min_opp))


async def statcast_running_splits(
    year: int,
    min_opp: int = 5,
    raw_splits: bool = True,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch Statcast running splits data.

    Edge Cases: When raw_splits is True, returns raw split times;
    when False, returns percentile-based splits.
    """
    split_type = "raw" if raw_splits else "percent"
    return await get_leaderboard("running_splits", context=context, type=split_type, year=str(year), min=str(min_opp))


async def statcast_base_stealing(
    year: int,
    min_attempts: int | str = "q",
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch Statcast base stealing run value leaderboard data."""
    return await get_leaderboard("base_stealing", context=context, year=str(year), min=str(min_attempts))


# Fielding APIs


_OAA_AGGREGATE_CODES = frozenset({"IF", "OF", "ALL", ""})


async def statcast_outs_above_average(
    year: int,
    pos: int | str,
    min_att: int | str = SAVANT_MIN_QUALIFYING,
    view: str = "Fielder",
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch Statcast Outs Above Average (OAA) leaderboard data.

    Edge Cases:
      - Does not support catchers (position code "2"); raises InvalidParameterError.
      - Does not support aggregate codes ("IF", "OF", "ALL"); the Savant OAA endpoint
        only accepts single numeric position codes (3–9). Use a specific position instead.
    """
    pos_code = pos_to_numeric(pos)
    if pos_code == "2":
        raise InvalidParameterError("This particular leaderboard does not include catchers!")
    if pos_code in _OAA_AGGREGATE_CODES:
        raise InvalidParameterError(
            f"statcast_outs_above_average requires a specific position (e.g. 'LF', 'CF', 'RF', '1B', '2B', '3B', 'SS'), "
            f"not an aggregate code '{pos}'. The Savant OAA API does not support aggregate position queries."
        )
    return await get_leaderboard(
        "outs_above_average",
        context=context,
        type=view,
        startYear=str(year),
        endYear=str(year),
        min=str(min_att),
        pos=pos_code,
    )


async def statcast_fielding_run_value(
    year: int,
    pos: int | str,
    min_inn: int = 100,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch Statcast fielding run value leaderboard data for a given position."""
    pos_code = pos_to_numeric(pos)
    return await get_leaderboard(
        "fielding_run_value",
        context=context,
        seasonStart=str(year),
        seasonEnd=str(year),
        position=pos_code,
        minInnings=str(min_inn),
    )


async def statcast_outfield_directional_oaa(
    year: int,
    min_opp: int | str = SAVANT_MIN_QUALIFYING,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch Statcast directional Outs Above Average (OAA) for outfielders."""
    return await get_leaderboard("directional_oaa", context=context, year=str(year), min=str(min_opp))


async def statcast_outfield_catch_prob(
    year: int,
    min_opp: int | str = SAVANT_MIN_QUALIFYING,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch Statcast outfield catch probability leaderboard data."""
    return await get_leaderboard("catch_probability", context=context, min=str(min_opp), year=str(year))


async def statcast_outfielder_jump(
    year: int,
    min_att: int | str = SAVANT_MIN_QUALIFYING,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch Statcast outfield jump (reaction time) leaderboard data."""
    return await get_leaderboard("outfielder_jump", context=context, year=str(year), min=str(min_att))


async def statcast_catcher_poptime(
    year: int,
    min_2b_att: int = 5,
    min_3b_att: int = 0,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch Statcast catcher pop time leaderboard data."""
    return await get_leaderboard(
        "poptime", context=context, year=str(year), min2b=str(min_2b_att), min3b=str(min_3b_att)
    )


async def statcast_catcher_framing(
    year: int,
    min_called_p: int | str = SAVANT_MIN_QUALIFYING,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch Statcast catcher framing leaderboard data.

    Edge Cases: Filters out rows with null/empty player name.
    """
    df = await get_leaderboard(
        "catcher_framing", context=context, seasonStart=str(year), seasonEnd=str(year), min=str(min_called_p)
    )
    if df.height > 0 and "name" in df.columns:
        df = df.filter(pl.col("name").is_not_null() & (pl.col("name").str.strip_chars() != ""))
    return df


async def statcast_catcher_blocking(
    year: int,
    min_chances: int = SAVANT_DEFAULT_CATCHER_BLOCKING_MIN,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch Statcast catcher blocking leaderboard data."""
    return await get_leaderboard("catcher_blocking", context=context, year=str(year), min_chances=str(min_chances))


async def statcast_arm_strength(
    year: int,
    min_throws: int = SAVANT_DEFAULT_ARM_STRENGTH_MIN,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch Statcast arm strength leaderboard data for fielders."""
    return await get_leaderboard("arm_strength", context=context, year=str(year), min=str(min_throws))


async def statcast_baserunning_run_value(
    year: int,
    min_opp: int = SAVANT_DEFAULT_BASERUNNING_MIN,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch Statcast baserunning run value leaderboard data."""
    return await get_leaderboard("baserunning_run_value", context=context, year=str(year), min=str(min_opp))


async def statcast_catcher_throwing(
    year: int,
    min_att: int = SAVANT_DEFAULT_CATCHER_THROWING_MIN,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch Statcast catcher throwing leaderboard data."""
    return await get_leaderboard("catcher_throwing", context=context, year=str(year), min_att=str(min_att))


async def statcast_catcher_stance(
    year: int,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch Statcast catcher stance leaderboard data."""
    return await get_leaderboard("catcher_stance", context=context, year=str(year))
