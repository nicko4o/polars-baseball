"""MLB taxonomy mixin (teams, divisions, leagues, venues, standings)."""

from __future__ import annotations

from typing import TYPE_CHECKING

import polars as pl

from polars_baseball._config import MLB_FIRST_YEAR, STATS_API_ROOT
from polars_baseball._mlb_contracts import (
    MLB_CACHE_MAX_AGE,
    MLB_DEFAULT_SPORT_ID,
    divisions_url,
    leagues_url,
    teams_url,
    venue_url,
    venues_url,
)
from polars_baseball._season import most_recent_season
from polars_baseball.exceptions import InvalidParameterError
from polars_baseball.parsers.mlb import (
    parse_mlb_divisions,
    parse_mlb_leagues,
    parse_mlb_teams,
    parse_mlb_venues,
)
from polars_baseball.parsers.standings import parse_standings_payload

if TYPE_CHECKING:
    from polars_baseball.client import BaseballClient
    from polars_baseball.gateways.mlb import MlbStatsGateway

_STANDINGS_URL = f"{STATS_API_ROOT}/standings"
_PRE_DEAD_BALL_START = MLB_FIRST_YEAR


def _validate_venue_ids(venue_ids: int | list[int] | None) -> None:
    if isinstance(venue_ids, int) and venue_ids <= 0:
        raise InvalidParameterError("venue_ids must be a positive integer.")
    if isinstance(venue_ids, list) and not all(isinstance(v, int) and v > 0 for v in venue_ids):
        raise InvalidParameterError("All venue IDs in list must be positive integers.")


class MlbTaxonomyMixin:
    """Methods for retrieving MLB league taxonomy, divisions, teams, venues, and standings."""

    _client: BaseballClient
    _gateway: MlbStatsGateway

    async def teams(
        self,
        season: int | None = None,
        league_id: int | None = None,
        sport_id: int = MLB_DEFAULT_SPORT_ID,
        force_update: bool = False,
    ) -> pl.DataFrame:
        """Fetch MLB team information from the Stats API."""
        if season is not None:
            if season <= 0:
                raise InvalidParameterError("season must be a positive integer.")
            if season < MLB_FIRST_YEAR or season > most_recent_season() + 1:
                raise InvalidParameterError(f"Invalid season: {season}.")
        if sport_id <= 0:
            raise InvalidParameterError("sport_id must be a positive integer.")

        url = teams_url()
        params: dict[str, object] = {"sportId": sport_id}
        if season is not None:
            params["season"] = season
        if league_id is not None:
            params["leagueId"] = league_id

        return await self._gateway.fetch(
            url,
            params,
            "Failed to fetch or parse MLB teams data",
            lambda d: parse_mlb_teams(d, season),
            use_cache=True,
            max_age=MLB_CACHE_MAX_AGE,
            force_update=force_update,
        )

    async def divisions(self, sport_id: int = MLB_DEFAULT_SPORT_ID, force_update: bool = False) -> pl.DataFrame:
        """Fetch official MLB division dimension metadata from the Stats API."""
        if sport_id <= 0:
            raise InvalidParameterError("sport_id must be a positive integer.")
        return await self._gateway.fetch(
            divisions_url(),
            {"sportId": sport_id},
            "Failed to fetch or parse MLB divisions data",
            parse_mlb_divisions,
            use_cache=True,
            max_age=MLB_CACHE_MAX_AGE,
            force_update=force_update,
        )

    async def leagues(self, sport_id: int = MLB_DEFAULT_SPORT_ID, force_update: bool = False) -> pl.DataFrame:
        """Fetch official MLB league dimension metadata from the Stats API."""
        if sport_id <= 0:
            raise InvalidParameterError("sport_id must be a positive integer.")
        return await self._gateway.fetch(
            leagues_url(),
            {"sportId": sport_id},
            "Failed to fetch or parse MLB leagues data",
            parse_mlb_leagues,
            use_cache=True,
            max_age=MLB_CACHE_MAX_AGE,
            force_update=force_update,
        )

    async def venues(
        self,
        venue_ids: int | list[int] | None = None,
        force_update: bool = False,
    ) -> pl.DataFrame:
        """Fetch MLB venue details."""
        _validate_venue_ids(venue_ids)
        if isinstance(venue_ids, int):
            url = venue_url(str(venue_ids))
            params: dict[str, object] = {}
        elif isinstance(venue_ids, list):
            url = venues_url()
            params = {"venueIds": ",".join(map(str, venue_ids))}
        else:
            url = venues_url()
            params = {}

        return await self._gateway.fetch(
            url,
            params,
            "Failed to fetch or parse MLB venues data",
            parse_mlb_venues,
            use_cache=True,
            max_age=MLB_CACHE_MAX_AGE,
            force_update=force_update,
        )

    async def standings(self, season: int | None = None, force_update: bool = False) -> pl.DataFrame:
        """Fetch division standings from the MLB Stats API."""
        if season is None:
            season = most_recent_season()
        if season < _PRE_DEAD_BALL_START:
            raise InvalidParameterError(
                f"This query currently only returns standings until the {_PRE_DEAD_BALL_START} season."
            )
        return await self._gateway.fetch(
            _STANDINGS_URL,
            params={"leagueId": "103,104", "season": season},
            error_msg="Failed to fetch or parse standings from MLB Stats API",
            parser=lambda payload: parse_standings_payload(payload, season),
            use_cache=True,
            force_update=force_update,
        )

    async def resolve_team_id(self, team_name: str) -> int:
        """Resolve an MLB team display name to a Stats API team id."""
        clean_name = team_name.replace(" ", "").replace("-", "").lower()
        teams_df = await self.teams(season=most_recent_season())
        norm_expr = pl.col("teamName").str.to_lowercase().str.replace_all(r"[ -]", "")
        filtered = teams_df.filter(norm_expr == clean_name)
        if filtered.is_empty():
            raise InvalidParameterError(f"Could not resolve team name: {team_name}")
        team_id = filtered["id"][0]
        if team_id is None or team_id == -1:
            raise InvalidParameterError(f"Could not resolve team name: {team_name}")
        return int(team_id)
