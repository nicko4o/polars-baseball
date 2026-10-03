"""Gateway for Retrosheet datasets."""

from __future__ import annotations

from polars_baseball._config import (
    RETROSHEET_CONTENTS_URL_TEMPLATE,
    RETROSHEET_EVENT_URL,
    RETROSHEET_GAMELOG_URL,
    RETROSHEET_PARKID_URL,
    RETROSHEET_ROSTER_URL,
    RETROSHEET_SCHEDULE_URL,
    RETROSHEET_SEASON_GAMELOG_URL,
)
from polars_baseball.context import BaseballContext
from polars_baseball.exceptions import UpstreamUnavailableError
from polars_baseball.gateways.base import BaseGateway
from polars_baseball.parsers.retrosheet import parse_season_contents


class RetrosheetGateway(BaseGateway):
    """Gateway for querying and caching raw data from Retrosheet."""

    def __init__(self, context: BaseballContext) -> None:
        super().__init__(context)

    async def get_season_contents(self, season: int) -> list[str]:
        url = RETROSHEET_CONTENTS_URL_TEMPLATE.format(season)
        headers = {}
        if self._context.github_token:
            headers["Authorization"] = f"token {self._context.github_token}"

        raw_bytes = await self._context.http.get_text(url, headers=headers)
        if not raw_bytes:
            raise UpstreamUnavailableError(f"Season {season} directory not found or empty.")
        return parse_season_contents(raw_bytes, season)

    async def get_event_file(self, season: int, filename: str, *, use_cache: bool = False) -> str:
        url = RETROSHEET_EVENT_URL.format(season, filename)
        return await self._fetch_cached_raw(
            url,
            use_cache=use_cache,
            error_msg="Retrosheet event file is empty.",
        )

    async def get_roster_file(self, season: int, team: str, *, use_cache: bool = False) -> str:
        url = RETROSHEET_ROSTER_URL.format(season, team, season)
        return await self._fetch_cached_raw(
            url,
            use_cache=use_cache,
            error_msg="Retrosheet roster file is empty.",
        )

    async def get_park_codes_csv(self, *, use_cache: bool = True) -> str:
        return await self._fetch_cached_raw(
            RETROSHEET_PARKID_URL,
            use_cache=use_cache,
            error_msg="Retrosheet park codes file is empty.",
        )

    async def get_schedule_csv(self, season: int, *, use_cache: bool = True) -> str:
        url = RETROSHEET_SCHEDULE_URL.format(season, season)
        return await self._fetch_cached_raw(
            url,
            use_cache=use_cache,
            error_msg="Retrosheet schedule file is empty.",
        )

    async def get_season_gamelog_csv(self, season: int, *, use_cache: bool = True) -> str:
        url = RETROSHEET_SEASON_GAMELOG_URL.format(season, season)
        return await self._fetch_cached_raw(
            url,
            use_cache=use_cache,
            error_msg="Retrosheet season game log file is empty.",
        )

    async def get_gamelog_csv(self, suffix: str, *, use_cache: bool = True) -> str:
        url = RETROSHEET_GAMELOG_URL.format(suffix)
        return await self._fetch_cached_raw(
            url,
            use_cache=use_cache,
            error_msg="Retrosheet gamelog file is empty.",
        )
