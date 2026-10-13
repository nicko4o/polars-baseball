from __future__ import annotations

from collections.abc import Sequence
from datetime import timedelta

import polars as pl

from polars_baseball._config import FG_MAX_RESULTS
from polars_baseball.apis.fangraphs import (
    FanGraphsFilterInput,
    FanGraphsRequest,
    fg_data,
)
from polars_baseball.context import BaseballContext
from polars_baseball.enums.fangraphs import (
    FangraphsLeague,
    FangraphsMonth,
    FangraphsPositions,
    FangraphsStatColumn,
    FangraphsStatsCategory,
)


async def _dispatch_fg(
    category: FangraphsStatsCategory,
    is_team_data: bool,
    raw_args: dict[str, object],
) -> pl.DataFrame:
    ctx = raw_args.get("context")
    context = ctx if isinstance(ctx, BaseballContext) or ctx is None else None
    force_update = bool(raw_args.get("force_update", False))
    max_age_raw = raw_args.get("cache_max_age")
    cache_max_age = max_age_raw if isinstance(max_age_raw, timedelta) or max_age_raw is None else None

    excluded = {"context", "force_update", "cache_max_age"}
    kwargs = {k: v for k, v in raw_args.items() if k not in excluded}
    request = FanGraphsRequest.from_raw(
        stats_category=category,
        is_team_data=is_team_data,
        **kwargs,  # type: ignore[arg-type]
    )
    return await fg_data(
        request,
        context=context,
        force_update=force_update,
        cache_max_age=cache_max_age,
    )


async def batting(
    start_season: int,
    *,
    end_season: int | None = None,
    league: str | FangraphsLeague = FangraphsLeague.ALL,
    month: str | FangraphsMonth = FangraphsMonth.ALL,
    position: str | FangraphsPositions = FangraphsPositions.ALL,
    stat_columns: str | list[str] | list[FangraphsStatColumn] = "ALL",
    qual: int | None = None,
    split_seasons: bool = True,
    on_active_roster: bool = False,
    minimum_age: int = 0,
    maximum_age: int = 100,
    filters: Sequence[FanGraphsFilterInput] | None = None,
    players: str = "",
    max_results: int = FG_MAX_RESULTS,
    context: BaseballContext | None = None,
    force_update: bool = False,
    cache_max_age: timedelta | None = None,
) -> pl.DataFrame:
    """Fetch FanGraphs batting leaderboard data for individual players."""
    return await _dispatch_fg(FangraphsStatsCategory.BATTING, False, locals())


async def pitching(
    start_season: int,
    *,
    end_season: int | None = None,
    league: str | FangraphsLeague = FangraphsLeague.ALL,
    month: str | FangraphsMonth = FangraphsMonth.ALL,
    position: str | FangraphsPositions = FangraphsPositions.ALL,
    stat_columns: str | list[str] | list[FangraphsStatColumn] = "ALL",
    qual: int | None = None,
    split_seasons: bool = True,
    on_active_roster: bool = False,
    minimum_age: int = 0,
    maximum_age: int = 100,
    filters: Sequence[FanGraphsFilterInput] | None = None,
    players: str = "",
    max_results: int = FG_MAX_RESULTS,
    context: BaseballContext | None = None,
    force_update: bool = False,
    cache_max_age: timedelta | None = None,
) -> pl.DataFrame:
    """Fetch FanGraphs pitching leaderboard data for individual players."""
    return await _dispatch_fg(FangraphsStatsCategory.PITCHING, False, locals())


async def fielding(
    start_season: int,
    *,
    end_season: int | None = None,
    league: str | FangraphsLeague = FangraphsLeague.ALL,
    month: str | FangraphsMonth = FangraphsMonth.ALL,
    position: str | FangraphsPositions = FangraphsPositions.ALL,
    stat_columns: str | list[str] | list[FangraphsStatColumn] = "ALL",
    qual: int | None = None,
    split_seasons: bool = True,
    on_active_roster: bool = False,
    minimum_age: int = 0,
    maximum_age: int = 100,
    filters: Sequence[FanGraphsFilterInput] | None = None,
    players: str = "",
    max_results: int = FG_MAX_RESULTS,
    context: BaseballContext | None = None,
    force_update: bool = False,
    cache_max_age: timedelta | None = None,
) -> pl.DataFrame:
    """Fetch FanGraphs fielding leaderboard data for individual players."""
    return await _dispatch_fg(FangraphsStatsCategory.FIELDING, False, locals())


async def team_batting(
    start_season: int,
    *,
    end_season: int | None = None,
    league: str | FangraphsLeague = FangraphsLeague.ALL,
    month: str | FangraphsMonth = FangraphsMonth.ALL,
    position: str | FangraphsPositions = FangraphsPositions.ALL,
    stat_columns: str | list[str] | list[FangraphsStatColumn] = "ALL",
    qual: int | None = None,
    split_seasons: bool = True,
    on_active_roster: bool = False,
    minimum_age: int = 0,
    maximum_age: int = 100,
    team: str = "",
    filters: Sequence[FanGraphsFilterInput] | None = None,
    players: str = "",
    max_results: int = FG_MAX_RESULTS,
    context: BaseballContext | None = None,
    force_update: bool = False,
    cache_max_age: timedelta | None = None,
) -> pl.DataFrame:
    """Fetch FanGraphs team batting leaderboard data."""
    return await _dispatch_fg(FangraphsStatsCategory.BATTING, True, locals())


async def team_pitching(
    start_season: int,
    *,
    end_season: int | None = None,
    league: str | FangraphsLeague = FangraphsLeague.ALL,
    month: str | FangraphsMonth = FangraphsMonth.ALL,
    position: str | FangraphsPositions = FangraphsPositions.ALL,
    stat_columns: str | list[str] | list[FangraphsStatColumn] = "ALL",
    qual: int | None = None,
    split_seasons: bool = True,
    on_active_roster: bool = False,
    minimum_age: int = 0,
    maximum_age: int = 100,
    team: str = "",
    filters: Sequence[FanGraphsFilterInput] | None = None,
    players: str = "",
    max_results: int = FG_MAX_RESULTS,
    context: BaseballContext | None = None,
    force_update: bool = False,
    cache_max_age: timedelta | None = None,
) -> pl.DataFrame:
    """Fetch FanGraphs team pitching leaderboard data."""
    return await _dispatch_fg(FangraphsStatsCategory.PITCHING, True, locals())


async def team_fielding(
    start_season: int,
    *,
    end_season: int | None = None,
    league: str | FangraphsLeague = FangraphsLeague.ALL,
    month: str | FangraphsMonth = FangraphsMonth.ALL,
    position: str | FangraphsPositions = FangraphsPositions.ALL,
    stat_columns: str | list[str] | list[FangraphsStatColumn] = "ALL",
    qual: int | None = None,
    split_seasons: bool = True,
    on_active_roster: bool = False,
    minimum_age: int = 0,
    maximum_age: int = 100,
    team: str = "",
    filters: Sequence[FanGraphsFilterInput] | None = None,
    players: str = "",
    max_results: int = FG_MAX_RESULTS,
    context: BaseballContext | None = None,
    force_update: bool = False,
    cache_max_age: timedelta | None = None,
) -> pl.DataFrame:
    """Fetch FanGraphs team fielding leaderboard data."""
    return await _dispatch_fg(FangraphsStatsCategory.FIELDING, True, locals())


async def team_starters(
    start_season: int,
    *,
    end_season: int | None = None,
    league: str | FangraphsLeague = FangraphsLeague.ALL,
    month: str | FangraphsMonth = FangraphsMonth.ALL,
    position: str | FangraphsPositions = FangraphsPositions.ALL,
    stat_columns: str | list[str] | list[FangraphsStatColumn] = "ALL",
    qual: int | None = None,
    split_seasons: bool = True,
    on_active_roster: bool = False,
    minimum_age: int = 0,
    maximum_age: int = 100,
    team: str = "",
    filters: Sequence[FanGraphsFilterInput] | None = None,
    players: str = "",
    max_results: int = FG_MAX_RESULTS,
    context: BaseballContext | None = None,
    force_update: bool = False,
    cache_max_age: timedelta | None = None,
) -> pl.DataFrame:
    """Fetch FanGraphs team starting pitcher leaderboard data."""
    return await _dispatch_fg(FangraphsStatsCategory.STARTERS, True, locals())


async def team_relievers(
    start_season: int,
    *,
    end_season: int | None = None,
    league: str | FangraphsLeague = FangraphsLeague.ALL,
    month: str | FangraphsMonth = FangraphsMonth.ALL,
    position: str | FangraphsPositions = FangraphsPositions.ALL,
    stat_columns: str | list[str] | list[FangraphsStatColumn] = "ALL",
    qual: int | None = None,
    split_seasons: bool = True,
    on_active_roster: bool = False,
    minimum_age: int = 0,
    maximum_age: int = 100,
    team: str = "",
    filters: Sequence[FanGraphsFilterInput] | None = None,
    players: str = "",
    max_results: int = FG_MAX_RESULTS,
    context: BaseballContext | None = None,
    force_update: bool = False,
    cache_max_age: timedelta | None = None,
) -> pl.DataFrame:
    """Fetch FanGraphs team relief pitcher leaderboard data."""
    return await _dispatch_fg(FangraphsStatsCategory.RELIEVERS, True, locals())


__all__ = [
    "batting",
    "fielding",
    "pitching",
    "team_batting",
    "team_fielding",
    "team_pitching",
    "team_relievers",
    "team_starters",
]
