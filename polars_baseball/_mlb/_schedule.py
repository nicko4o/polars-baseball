"""MLB schedule and postseason calendar mixin."""

from __future__ import annotations

import re
from datetime import date
from typing import TYPE_CHECKING

import polars as pl

from polars_baseball._config import MLB_FIRST_YEAR
from polars_baseball._mlb_contracts import (
    MLB_CACHE_MAX_AGE,
    MLB_DEFAULT_SPORT_ID,
    MLB_POSTSEASON_GAME_TYPE,
    schedule_url,
)
from polars_baseball._season import coerce_datestring, most_recent_season
from polars_baseball.exceptions import InvalidParameterError
from polars_baseball.parsers.mlb import parse_mlb_schedule

if TYPE_CHECKING:
    from polars_baseball.client import BaseballClient
    from polars_baseball.gateways.mlb import MlbStatsGateway


class MlbScheduleMixin:
    """Methods for retrieving MLB regular season and postseason schedules."""

    _client: BaseballClient
    _gateway: MlbStatsGateway

    async def schedule(
        self,
        season: int | None = None,
        date: date | str | None = None,
        team_id: int | None = None,
        hydrate: str | None = None,
        force_update: bool = False,
    ) -> pl.DataFrame:
        """Fetch MLB schedule."""
        coerced_date = coerce_datestring(date)
        if season is None and coerced_date is None:
            raise InvalidParameterError("Either season or date must be provided.")
        if season is not None and coerced_date is not None:
            raise InvalidParameterError("Cannot specify both season and date.")
        if season is not None and (season < MLB_FIRST_YEAR or season > most_recent_season() + 1):
            raise InvalidParameterError(f"Invalid season: {season}.")
        if coerced_date is not None and not re.match(r"^\d{4}-\d{2}-\d{2}$", coerced_date):
            raise InvalidParameterError("date must be in YYYY-MM-DD format.")
        if team_id is not None and team_id <= 0:
            raise InvalidParameterError("team_id must be a positive integer.")

        params: dict[str, object] = {"sportId": MLB_DEFAULT_SPORT_ID}
        if season is not None:
            params["season"] = season
        if coerced_date is not None:
            params["date"] = coerced_date
        if team_id is not None:
            params["teamId"] = team_id
        if hydrate is not None:
            params["hydrate"] = hydrate

        return await self._gateway.fetch(
            schedule_url(),
            params,
            "Failed to fetch or parse MLB schedule data",
            parse_mlb_schedule,
            use_cache=True,
            max_age=MLB_CACHE_MAX_AGE,
            force_update=force_update,
        )

    async def postseason_schedule(self, season: int, force_update: bool = False) -> pl.DataFrame:
        """Fetch MLB postseason schedule."""
        if season < MLB_FIRST_YEAR or season > most_recent_season() + 1:
            raise InvalidParameterError(f"Invalid season: {season}.")

        params: dict[str, object] = {
            "gameType": MLB_POSTSEASON_GAME_TYPE,
            "sportId": MLB_DEFAULT_SPORT_ID,
            "season": season,
        }
        return await self._gateway.fetch(
            schedule_url(),
            params,
            "Failed to fetch or parse MLB postseason schedule data",
            parse_mlb_schedule,
            use_cache=True,
            max_age=MLB_CACHE_MAX_AGE,
            force_update=force_update,
        )
