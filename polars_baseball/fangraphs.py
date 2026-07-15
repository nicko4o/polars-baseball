from __future__ import annotations

import polars as pl

from polars_baseball._config import FG_MAX_RESULTS
from polars_baseball.apis.fangraphs import FanGraphsRequest, fg_data
from polars_baseball.context import BaseballContext
from polars_baseball.enums.fangraphs import (
    FangraphsLeague,
    FangraphsMonth,
    FangraphsPositions,
    FangraphsStatColumn,
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
    max_results: int = FG_MAX_RESULTS,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch FanGraphs batting leaderboard data."""
    request = FanGraphsRequest.batting(
        start_season=start_season,
        end_season=end_season,
        league=league,
        month=month,
        position=position,
        stat_columns=stat_columns,
        qual=qual,
        split_seasons=split_seasons,
        max_results=max_results,
    )
    return await fg_data(request, context=context)


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
    max_results: int = FG_MAX_RESULTS,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch FanGraphs pitching leaderboard data."""
    request = FanGraphsRequest.pitching(
        start_season=start_season,
        end_season=end_season,
        league=league,
        month=month,
        position=position,
        stat_columns=stat_columns,
        qual=qual,
        split_seasons=split_seasons,
        max_results=max_results,
    )
    return await fg_data(request, context=context)


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
    max_results: int = FG_MAX_RESULTS,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch FanGraphs fielding leaderboard data."""
    request = FanGraphsRequest.fielding(
        start_season=start_season,
        end_season=end_season,
        league=league,
        month=month,
        position=position,
        stat_columns=stat_columns,
        qual=qual,
        split_seasons=split_seasons,
        max_results=max_results,
    )
    return await fg_data(request, context=context)


async def team_batting(
    start_season: int,
    *,
    end_season: int | None = None,
    league: str | FangraphsLeague = FangraphsLeague.ALL,
    month: str | FangraphsMonth = FangraphsMonth.ALL,
    qual: int | None = None,
    split_seasons: bool = True,
    team: str = "",
    max_results: int = FG_MAX_RESULTS,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch FanGraphs team batting leaderboard data."""
    request = FanGraphsRequest.team_batting(
        start_season=start_season,
        end_season=end_season,
        league=league,
        month=month,
        qual=qual,
        split_seasons=split_seasons,
        team=team,
        max_results=max_results,
    )
    return await fg_data(request, context=context)


async def team_pitching(
    start_season: int,
    *,
    end_season: int | None = None,
    league: str | FangraphsLeague = FangraphsLeague.ALL,
    month: str | FangraphsMonth = FangraphsMonth.ALL,
    qual: int | None = None,
    split_seasons: bool = True,
    team: str = "",
    max_results: int = FG_MAX_RESULTS,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch FanGraphs team pitching leaderboard data."""
    request = FanGraphsRequest.team_pitching(
        start_season=start_season,
        end_season=end_season,
        league=league,
        month=month,
        qual=qual,
        split_seasons=split_seasons,
        team=team,
        max_results=max_results,
    )
    return await fg_data(request, context=context)


async def team_fielding(
    start_season: int,
    *,
    end_season: int | None = None,
    league: str | FangraphsLeague = FangraphsLeague.ALL,
    month: str | FangraphsMonth = FangraphsMonth.ALL,
    qual: int | None = None,
    split_seasons: bool = True,
    team: str = "",
    max_results: int = FG_MAX_RESULTS,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch FanGraphs team fielding leaderboard data."""
    request = FanGraphsRequest.team_fielding(
        start_season=start_season,
        end_season=end_season,
        league=league,
        month=month,
        qual=qual,
        split_seasons=split_seasons,
        team=team,
        max_results=max_results,
    )
    return await fg_data(request, context=context)


__all__ = [
    "batting",
    "fielding",
    "pitching",
    "team_batting",
    "team_fielding",
    "team_pitching",
]
