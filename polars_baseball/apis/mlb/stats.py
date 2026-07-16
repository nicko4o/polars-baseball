import re

import polars as pl

from polars_baseball._cache import cached
from polars_baseball._config import MLB_FIRST_YEAR
from polars_baseball._season import most_recent_season
from polars_baseball.apis.mlb._contracts import (
    MLB_CACHE_MAX_AGE,
    MLB_DEFAULT_LEADER_LIMIT,
    MLB_DEFAULT_STATS_GROUP,
    MLB_DEFAULT_STATS_TYPE,
    MLB_PITCH_ARSENAL_STATS,
    people_stats_url,
    pitch_arsenal_cache_key,
    player_stats_cache_key,
    stat_leaders_cache_key,
    stat_leaders_url,
    team_stats_cache_key,
    team_stats_url,
)
from polars_baseball.context import BaseballContext, default_context
from polars_baseball.exceptions import InvalidParameterError
from polars_baseball.gateways.mlb import MlbStatsGateway
from polars_baseball.parsers.mlb import (
    parse_mlb_pitch_arsenal,
    parse_mlb_player_stats,
    parse_mlb_stat_leaders,
    parse_mlb_team_stats,
)


@cached(key=player_stats_cache_key, max_age=MLB_CACHE_MAX_AGE)
async def _fetch_mlb_player_stats(
    person_id: int,
    group: str,
    stats_type: str = MLB_DEFAULT_STATS_TYPE,
    season: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    force_update: bool = False,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    url = people_stats_url(person_id)
    params: dict[str, object] = {"stats": stats_type, "group": group}
    if season is not None:
        params["season"] = season
    if start_date is not None:
        params["startDate"] = start_date
    if end_date is not None:
        params["endDate"] = end_date
    ctx = context or default_context()
    return await MlbStatsGateway(ctx).fetch(
        url,
        params,
        "Failed to fetch or parse MLB player stats",
        lambda d: parse_mlb_player_stats(d, person_id, group, stats_type),
    )


async def mlb_player_stats(
    person_id: int,
    group: str,
    stats_type: str = MLB_DEFAULT_STATS_TYPE,
    season: int | None = None,
    start_date: str | None = None,
    end_date: str | None = None,
    force_update: bool = False,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch player stats from the MLB Stats API for a given stat group."""
    if person_id <= 0:
        raise InvalidParameterError("person_id must be a positive integer.")
    if not group:
        raise InvalidParameterError("group must be a non-empty string.")
    if not stats_type:
        raise InvalidParameterError("stats_type must be a non-empty string.")
    if season is not None and (season < MLB_FIRST_YEAR or season > most_recent_season() + 1):
        raise InvalidParameterError(f"Invalid season: {season}.")
    if start_date is not None and not re.match(r"^\d{4}-\d{2}-\d{2}$", start_date):
        raise InvalidParameterError("start_date must be in YYYY-MM-DD format.")
    if end_date is not None and not re.match(r"^\d{4}-\d{2}-\d{2}$", end_date):
        raise InvalidParameterError("end_date must be in YYYY-MM-DD format.")

    return await _fetch_mlb_player_stats(
        person_id=person_id,
        group=group,
        stats_type=stats_type,
        season=season,
        start_date=start_date,
        end_date=end_date,
        force_update=force_update,
        context=context,
    )


@cached(key=team_stats_cache_key, max_age=MLB_CACHE_MAX_AGE)
async def _fetch_mlb_team_stats(
    team_id: int,
    season: int | None = None,
    group: str = MLB_DEFAULT_STATS_GROUP,
    stats_type: str = MLB_DEFAULT_STATS_TYPE,
    force_update: bool = False,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    url = team_stats_url(team_id)
    params: dict[str, object] = {"group": group, "stats": stats_type}
    if season is not None:
        params["season"] = season
    ctx = context or default_context()
    return await MlbStatsGateway(ctx).fetch(
        url, params, "Failed to fetch or parse MLB team stats", lambda d: parse_mlb_team_stats(d, team_id, group)
    )


@cached(key=stat_leaders_cache_key, max_age=MLB_CACHE_MAX_AGE)
async def _fetch_mlb_stat_leaders(
    season: int,
    categories: list[str],
    limit: int = MLB_DEFAULT_LEADER_LIMIT,
    stat_group: str | None = None,
    force_update: bool = False,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    url = stat_leaders_url()
    params: dict[str, object] = {
        "leaderCategories": ",".join(categories),
        "limit": limit,
        "season": season,
    }
    if stat_group is not None:
        params["statGroup"] = stat_group
    ctx = context or default_context()
    return await MlbStatsGateway(ctx).fetch(
        url,
        params,
        "Failed to fetch or parse MLB stat leaders",
        lambda d: parse_mlb_stat_leaders(d, season, stat_group),
    )


async def mlb_stat_leaders(
    season: int,
    categories: list[str],
    limit: int = MLB_DEFAULT_LEADER_LIMIT,
    stat_group: str | None = None,
    force_update: bool = False,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch league leaders for one or more statistical categories.

    The stat_group parameter further scopes results (e.g. "hitting",
    "pitching"). Returns an empty DataFrame when no leader data is
    available for the given season and categories.

    Edge Cases:
        Raises InvalidParameterError if the season is out of range,
        categories is empty, or limit is non-positive.
    """
    if season < MLB_FIRST_YEAR or season > most_recent_season() + 1:
        raise InvalidParameterError(f"Invalid season: {season}.")
    if not categories:
        raise InvalidParameterError("categories must not be empty.")
    if limit <= 0:
        raise InvalidParameterError("limit must be a positive integer.")

    return await _fetch_mlb_stat_leaders(
        season=season,
        categories=categories,
        limit=limit,
        stat_group=stat_group,
        force_update=force_update,
        context=context,
    )


async def mlb_team_stats(
    team_id: int,
    season: int | None = None,
    group: str = MLB_DEFAULT_STATS_GROUP,
    stats_type: str = MLB_DEFAULT_STATS_TYPE,
    force_update: bool = False,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch team-level stats from the MLB Stats API.

    The group parameter specifies the stat category (e.g. "hitting",
    "pitching", "fielding"). The stats_type parameter controls the time
    frame (e.g. "season", "career").

    Edge Cases:
        Raises InvalidParameterError if team_id is non-positive, the
        season is out of range, or group or stats_type is empty.
    """
    if team_id <= 0:
        raise InvalidParameterError("team_id must be a positive integer.")
    if season is not None and (season < MLB_FIRST_YEAR or season > most_recent_season() + 1):
        raise InvalidParameterError(f"Invalid season: {season}.")
    if not group:
        raise InvalidParameterError("group must be a non-empty string.")
    if not stats_type:
        raise InvalidParameterError("stats_type must be a non-empty string.")

    return await _fetch_mlb_team_stats(
        team_id=team_id,
        season=season,
        group=group,
        stats_type=stats_type,
        force_update=force_update,
        context=context,
    )


@cached(key=pitch_arsenal_cache_key, max_age=MLB_CACHE_MAX_AGE)
async def _fetch_mlb_pitch_arsenal(
    person_id: int,
    season: int,
    force_update: bool = False,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    url = people_stats_url(person_id)
    params = {"stats": MLB_PITCH_ARSENAL_STATS, "season": season}
    ctx = context or default_context()
    return await MlbStatsGateway(ctx).fetch(
        url,
        params,
        "Failed to fetch or parse MLB pitch arsenal data",
        lambda d: parse_mlb_pitch_arsenal(d, person_id, season),
    )


async def mlb_pitch_arsenal(
    person_id: int,
    season: int,
    force_update: bool = False,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch pitch arsenal details for a player and season from the MLB Stats API.

    Args:
        person_id: The player's MLB ID (e.g. 545361).
        season: The season (e.g. 2024).
        force_update: Bypass cache and fetch fresh data.
        context: Optional BaseballContext.
    """
    if person_id <= 0:
        raise InvalidParameterError("person_id must be a positive integer.")
    if season < MLB_FIRST_YEAR or season > most_recent_season() + 1:
        raise InvalidParameterError(f"Invalid season: {season}.")

    return await _fetch_mlb_pitch_arsenal(
        person_id=person_id,
        season=season,
        force_update=force_update,
        context=context,
    )
