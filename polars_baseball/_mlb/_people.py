"""MLB people, awards, and roster mixin."""

from __future__ import annotations

from typing import TYPE_CHECKING

import polars as pl

from polars_baseball._config import MLB_FIRST_YEAR
from polars_baseball._mlb_contracts import (
    MLB_ACTIVE_ROSTER_TYPE,
    MLB_CACHE_MAX_AGE,
    people_awards_url,
    people_url,
    roster_url,
)
from polars_baseball._season import most_recent_season
from polars_baseball.enums.mlb import MlbRosterType, resolve_roster_type
from polars_baseball.exceptions import InvalidParameterError
from polars_baseball.parsers.mlb import (
    parse_mlb_people,
    parse_mlb_people_awards,
    parse_mlb_roster,
)

if TYPE_CHECKING:
    from polars_baseball.client import BaseballClient
    from polars_baseball.gateways.mlb import MlbStatsGateway


class MlbPeopleMixin:
    """Methods for retrieving MLB people, award timelines, and rosters."""

    _client: BaseballClient
    _gateway: MlbStatsGateway

    async def people(self, person_ids: list[int] | int, force_update: bool = False) -> pl.DataFrame:
        """Fetch MLB people metadata."""
        if not person_ids:
            raise InvalidParameterError("person_ids must not be empty.")
        if isinstance(person_ids, list):
            for pid in person_ids:
                if not isinstance(pid, int) or pid <= 0:
                    raise InvalidParameterError(f"Invalid player ID: {pid}. Must be positive integer.")
            ids_str = ",".join(map(str, person_ids))
        else:
            if not isinstance(person_ids, int) or person_ids <= 0:
                raise InvalidParameterError(f"Invalid player ID: {person_ids}. Must be positive integer.")
            ids_str = str(person_ids)

        return await self._gateway.fetch(
            people_url(),
            {"personIds": ids_str},
            "Failed to fetch or parse MLB people data",
            parse_mlb_people,
            use_cache=True,
            max_age=MLB_CACHE_MAX_AGE,
            force_update=force_update,
        )

    async def people_awards(self, person_id: int, force_update: bool = False) -> pl.DataFrame:
        """Fetch official MLB award timeline rows for a single person."""
        if person_id <= 0:
            raise InvalidParameterError("person_id must be a positive integer.")
        url = people_awards_url(person_id)
        return await self._gateway.fetch(
            url,
            None,
            "Failed to fetch or parse MLB people awards data",
            lambda d: parse_mlb_people_awards(d, person_id),
            use_cache=True,
            max_age=MLB_CACHE_MAX_AGE,
            force_update=force_update,
        )

    async def roster(
        self,
        team_id: int,
        season: int | None = None,
        roster_type: str | MlbRosterType = MLB_ACTIVE_ROSTER_TYPE,
        force_update: bool = False,
    ) -> pl.DataFrame:
        """Fetch team roster from the MLB Stats API."""
        if team_id <= 0:
            raise InvalidParameterError("team_id must be a positive integer.")
        if season is not None and (season < MLB_FIRST_YEAR or season > most_recent_season() + 1):
            raise InvalidParameterError(f"Invalid season: {season}.")
        resolved_type = resolve_roster_type(roster_type)

        url = roster_url(team_id)
        params: dict[str, object] = {"rosterType": resolved_type}
        if season is not None:
            params["season"] = season

        return await self._gateway.fetch(
            url,
            params,
            "Failed to fetch or parse MLB roster data",
            lambda d: parse_mlb_roster(d, team_id),
            use_cache=True,
            max_age=MLB_CACHE_MAX_AGE,
            force_update=force_update,
        )
