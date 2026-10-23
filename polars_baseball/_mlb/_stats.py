"""MLB statistics mixin (player stats, pitch arsenal, team stats, stat leaders)."""

from __future__ import annotations

import re
from datetime import date
from typing import TYPE_CHECKING

import polars as pl

from polars_baseball._config import MLB_FIRST_YEAR
from polars_baseball._mlb_contracts import (
    MLB_CACHE_MAX_AGE,
    MLB_DEFAULT_STATS_TYPE,
    MLB_PITCH_ARSENAL_STATS,
    people_stats_url,
    stat_leaders_url,
    team_stats_url,
)
from polars_baseball._season import coerce_datestring, most_recent_season
from polars_baseball.enums.mlb import MlbStatsGroup, resolve_group
from polars_baseball.exceptions import InvalidParameterError
from polars_baseball.parsers.mlb import (
    parse_mlb_pitch_arsenal,
    parse_mlb_player_stats,
    parse_mlb_stat_leaders,
    parse_mlb_team_stats,
)

if TYPE_CHECKING:
    from polars_baseball.client import BaseballClient
    from polars_baseball.gateways.mlb import MlbStatsGateway


class MlbStatsMixin:
    """Methods for retrieving MLB player and team statistical leaderboards and splits."""

    _client: BaseballClient
    _gateway: MlbStatsGateway

    async def player_stats(
        self,
        person_id: int,
        group: str | MlbStatsGroup = "hitting",
        stats_type: str = MLB_DEFAULT_STATS_TYPE,
        season: int | None = None,
        start_date: date | str | None = None,
        end_date: date | str | None = None,
        force_update: bool = False,
    ) -> pl.DataFrame:
        """Fetch player stats from the MLB Stats API for a given stat group."""
        s_date = coerce_datestring(start_date)
        e_date = coerce_datestring(end_date)
        if person_id <= 0:
            raise InvalidParameterError("person_id must be a positive integer.")
        resolved_grp = resolve_group(group)
        if not stats_type:
            raise InvalidParameterError("stats_type must be a non-empty string.")
        if season is not None and (season < MLB_FIRST_YEAR or season > most_recent_season() + 1):
            raise InvalidParameterError(f"Invalid season: {season}.")
        if s_date is not None and not re.match(r"^\d{4}-\d{2}-\d{2}$", s_date):
            raise InvalidParameterError("start_date must be in YYYY-MM-DD format.")
        if e_date is not None and not re.match(r"^\d{4}-\d{2}-\d{2}$", e_date):
            raise InvalidParameterError("end_date must be in YYYY-MM-DD format.")

        url = people_stats_url(person_id)
        params: dict[str, object] = {"stats": stats_type, "group": resolved_grp}
        if season is not None:
            params["season"] = season
        if s_date is not None:
            params["startDate"] = s_date
        if e_date is not None:
            params["endDate"] = e_date

        return await self._gateway.fetch(
            url,
            params,
            "Failed to fetch or parse MLB player stats",
            lambda d: parse_mlb_player_stats(d, person_id, resolved_grp, stats_type),
            use_cache=True,
            max_age=MLB_CACHE_MAX_AGE,
            force_update=force_update,
        )

    async def pitch_arsenal(
        self,
        person_id: int,
        season: int,
        force_update: bool = False,
    ) -> pl.DataFrame:
        """Fetch pitcher pitch arsenal statistics from the MLB Stats API."""
        if person_id <= 0:
            raise InvalidParameterError("person_id must be a positive integer.")
        if season < MLB_FIRST_YEAR or season > most_recent_season() + 1:
            raise InvalidParameterError(f"Invalid season: {season}.")

        url = people_stats_url(person_id)
        params: dict[str, object] = {"stats": MLB_PITCH_ARSENAL_STATS, "season": season}
        return await self._gateway.fetch(
            url,
            params,
            "Failed to fetch or parse MLB pitch arsenal stats",
            lambda d: parse_mlb_pitch_arsenal(d, person_id, season),
            use_cache=True,
            max_age=MLB_CACHE_MAX_AGE,
            force_update=force_update,
        )

    async def team_stats(
        self,
        team_id: int,
        season: int | None = None,
        group: str = "hitting",
        stats_type: str = MLB_DEFAULT_STATS_TYPE,
        force_update: bool = False,
    ) -> pl.DataFrame:
        """Fetch aggregate season stats for an MLB team."""
        if team_id <= 0:
            raise InvalidParameterError("team_id must be a positive integer.")
        if season is not None and (season < MLB_FIRST_YEAR or season > most_recent_season() + 1):
            raise InvalidParameterError(f"Invalid season: {season}.")
        resolved_grp = resolve_group(group)
        if not stats_type:
            raise InvalidParameterError("stats_type must be a non-empty string.")

        url = team_stats_url(team_id)
        params: dict[str, object] = {"group": resolved_grp, "stats": stats_type}
        if season is not None:
            params["season"] = season

        return await self._gateway.fetch(
            url,
            params,
            "Failed to fetch or parse MLB team stats",
            lambda d: parse_mlb_team_stats(d, team_id, resolved_grp),
            use_cache=True,
            max_age=MLB_CACHE_MAX_AGE,
            force_update=force_update,
        )

    async def stat_leaders(
        self,
        categories: list[str] | None = None,
        season: int | None = None,
        stat_group: str | None = None,
        limit: int = 10,
        force_update: bool = False,
        leader_categories: str | list[str] | None = None,
    ) -> pl.DataFrame:
        """Fetch MLB stat leaders for one or more statistical categories."""
        raw_cats = leader_categories if leader_categories is not None else categories
        cats: list[str] | None = [raw_cats] if isinstance(raw_cats, str) else raw_cats
        if cats is not None:
            cats = [c for c in cats if c]

        if not cats:
            raise InvalidParameterError("leader_categories must not be empty.")
        if season is not None and (season < MLB_FIRST_YEAR or season > most_recent_season() + 1):
            raise InvalidParameterError(f"Invalid season: {season}.")
        if limit <= 0:
            raise InvalidParameterError("limit must be a positive integer.")

        resolved_season = season if season is not None else most_recent_season()
        params: dict[str, object] = {
            "leaderCategories": ",".join(cats),
            "limit": limit,
            "season": resolved_season,
        }
        if stat_group is not None:
            params["statGroup"] = stat_group

        return await self._gateway.fetch(
            stat_leaders_url(),
            params,
            "Failed to fetch or parse MLB stat leaders",
            lambda d: parse_mlb_stat_leaders(d, resolved_season, stat_group),
            use_cache=True,
            max_age=MLB_CACHE_MAX_AGE,
            force_update=force_update,
        )
