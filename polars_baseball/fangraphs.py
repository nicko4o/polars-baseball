from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import timedelta

import polars as pl

from polars_baseball._config import FG_MAX_RESULTS
from polars_baseball.apis.fangraphs import (
    FanGraphsFilter,
    FanGraphsFilterInput,
    FanGraphsFilterOp,
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


@dataclass(frozen=True)
class FanGraphsLeaderboardParams:
    start_season: int
    end_season: int | None = None
    league: str | FangraphsLeague = FangraphsLeague.ALL
    month: str | FangraphsMonth = FangraphsMonth.ALL
    position: str | FangraphsPositions = FangraphsPositions.ALL
    stat_columns: str | list[str] | list[FangraphsStatColumn] = "ALL"
    qual: int | None = None
    split_seasons: bool = True
    on_active_roster: bool = False
    minimum_age: int = 0
    maximum_age: int = 100
    team: str = ""
    filters: Sequence[FanGraphsFilterInput] | None = None
    players: str = ""
    max_results: int = FG_MAX_RESULTS
    ind: int = 1


async def _dispatch_fg(
    category: FangraphsStatsCategory,
    is_team_data: bool,
    params: FanGraphsLeaderboardParams,
    context: BaseballContext | None,
    force_update: bool,
    cache_max_age: timedelta | None,
) -> pl.DataFrame:
    return await fg_data(
        params.start_season,
        end_season=params.end_season,
        stats_category=category,
        league=params.league,
        month=params.month,
        position=params.position,
        stat_columns=params.stat_columns,
        qual=params.qual,
        split_seasons=params.split_seasons,
        ind=params.ind,
        on_active_roster=params.on_active_roster,
        minimum_age=params.minimum_age,
        maximum_age=params.maximum_age,
        team=params.team,
        filters=params.filters,
        players=params.players,
        max_results=params.max_results,
        is_team_data=is_team_data,
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
    params = FanGraphsLeaderboardParams(
        start_season=start_season,
        end_season=end_season,
        league=league,
        month=month,
        position=position,
        stat_columns=stat_columns,
        qual=qual,
        split_seasons=split_seasons,
        on_active_roster=on_active_roster,
        minimum_age=minimum_age,
        maximum_age=maximum_age,
        filters=filters,
        players=players,
        max_results=max_results,
    )
    return await _dispatch_fg(FangraphsStatsCategory.BATTING, False, params, context, force_update, cache_max_age)


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
    params = FanGraphsLeaderboardParams(
        start_season=start_season,
        end_season=end_season,
        league=league,
        month=month,
        position=position,
        stat_columns=stat_columns,
        qual=qual,
        split_seasons=split_seasons,
        on_active_roster=on_active_roster,
        minimum_age=minimum_age,
        maximum_age=maximum_age,
        filters=filters,
        players=players,
        max_results=max_results,
    )
    return await _dispatch_fg(FangraphsStatsCategory.PITCHING, False, params, context, force_update, cache_max_age)


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
    params = FanGraphsLeaderboardParams(
        start_season=start_season,
        end_season=end_season,
        league=league,
        month=month,
        position=position,
        stat_columns=stat_columns,
        qual=qual,
        split_seasons=split_seasons,
        on_active_roster=on_active_roster,
        minimum_age=minimum_age,
        maximum_age=maximum_age,
        filters=filters,
        players=players,
        max_results=max_results,
    )
    return await _dispatch_fg(FangraphsStatsCategory.FIELDING, False, params, context, force_update, cache_max_age)


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
    params = FanGraphsLeaderboardParams(
        start_season=start_season,
        end_season=end_season,
        league=league,
        month=month,
        position=position,
        stat_columns=stat_columns,
        qual=qual,
        split_seasons=split_seasons,
        on_active_roster=on_active_roster,
        minimum_age=minimum_age,
        maximum_age=maximum_age,
        team=team,
        filters=filters,
        players=players,
        max_results=max_results,
    )
    return await _dispatch_fg(FangraphsStatsCategory.BATTING, True, params, context, force_update, cache_max_age)


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
    params = FanGraphsLeaderboardParams(
        start_season=start_season,
        end_season=end_season,
        league=league,
        month=month,
        position=position,
        stat_columns=stat_columns,
        qual=qual,
        split_seasons=split_seasons,
        on_active_roster=on_active_roster,
        minimum_age=minimum_age,
        maximum_age=maximum_age,
        team=team,
        filters=filters,
        players=players,
        max_results=max_results,
    )
    return await _dispatch_fg(FangraphsStatsCategory.PITCHING, True, params, context, force_update, cache_max_age)


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
    params = FanGraphsLeaderboardParams(
        start_season=start_season,
        end_season=end_season,
        league=league,
        month=month,
        position=position,
        stat_columns=stat_columns,
        qual=qual,
        split_seasons=split_seasons,
        on_active_roster=on_active_roster,
        minimum_age=minimum_age,
        maximum_age=maximum_age,
        team=team,
        filters=filters,
        players=players,
        max_results=max_results,
    )
    return await _dispatch_fg(FangraphsStatsCategory.FIELDING, True, params, context, force_update, cache_max_age)


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
    params = FanGraphsLeaderboardParams(
        start_season=start_season,
        end_season=end_season,
        league=league,
        month=month,
        position=position,
        stat_columns=stat_columns,
        qual=qual,
        split_seasons=split_seasons,
        on_active_roster=on_active_roster,
        minimum_age=minimum_age,
        maximum_age=maximum_age,
        team=team,
        filters=filters,
        players=players,
        max_results=max_results,
    )
    return await _dispatch_fg(FangraphsStatsCategory.STARTERS, True, params, context, force_update, cache_max_age)


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
    params = FanGraphsLeaderboardParams(
        start_season=start_season,
        end_season=end_season,
        league=league,
        month=month,
        position=position,
        stat_columns=stat_columns,
        qual=qual,
        split_seasons=split_seasons,
        on_active_roster=on_active_roster,
        minimum_age=minimum_age,
        maximum_age=maximum_age,
        team=team,
        filters=filters,
        players=players,
        max_results=max_results,
    )
    return await _dispatch_fg(FangraphsStatsCategory.RELIEVERS, True, params, context, force_update, cache_max_age)


__all__ = [
    "FanGraphsFilter",
    "FanGraphsFilterOp",
    "batting",
    "fg_data",
    "fielding",
    "pitching",
    "team_batting",
    "team_fielding",
    "team_pitching",
    "team_relievers",
    "team_starters",
]
