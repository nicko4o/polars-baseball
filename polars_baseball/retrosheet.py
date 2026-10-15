"""Namespaced client for Retrosheet endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING

import polars as pl

from polars_baseball._cache import generate_cache_key
from polars_baseball._concurrency import bounded_gather
from polars_baseball.exceptions import (
    InvalidParameterError,
    ServerError,
)
from polars_baseball.gateways.retrosheet import RetrosheetGateway
from polars_baseball.parsers.retrosheet import (
    empty_rosters_frame,
    event_content_row,
    events_frame,
    parse_gamelog_csv,
    parse_park_codes_csv,
    parse_roster_csv,
    parse_schedule_csv,
)

if TYPE_CHECKING:
    from polars_baseball.client import BaseballClient

_RETROSHEET_GAME_TYPE_EXTENSIONS: dict[str, tuple[str, ...]] = {
    "regular": (".EVA", ".EVN"),
    "post": ("CS.EVE", "D1.EVE", "D2.EVE", "W1.EVE", "W2.EVE", "WS.EVE"),
    "asg": ("AS.EVE",),
}


class RetrosheetClient:
    """Namespaced Retrosheet client."""

    def __init__(self, client: BaseballClient) -> None:
        self._client = client

    async def events(
        self,
        season: int,
        game_type: str = "regular",
        force_update: bool = False,
        *,
        concurrency_limit: int = 5,
    ) -> pl.DataFrame:
        """Fetch Retrosheet event files for a given season."""
        if game_type not in _RETROSHEET_GAME_TYPE_EXTENSIONS:
            raise InvalidParameterError(
                f"Illegal type argument {game_type}, the valid types are: 'regular', 'post', and 'asg'."
            )
        gateway = RetrosheetGateway(self._client)

        async def _fetch_events() -> pl.DataFrame:
            files = await gateway.get_season_contents(season)
            file_extensions = _RETROSHEET_GAME_TYPE_EXTENSIONS[game_type]

            season_events = [t for t in files if t.endswith(file_extensions)]
            if not season_events:
                raise ServerError(f"Event files not available for {season}")

            async def _fetch_event(filename: str) -> dict[str, object]:
                raw = await gateway.get_event_file(season, filename)
                return event_content_row(season, game_type, filename, raw)

            tasks = [lambda f=f: _fetch_event(f) for f in season_events]
            results = await bounded_gather(tasks, concurrency_limit=concurrency_limit)
            rows = [row for row in results if row is not None]
            return events_frame(rows)

        key = generate_cache_key("retrosheet/events", {"season": season, "game_type": game_type})
        return await self._client.cache.get_or_fetch(key, _fetch_events, force_update=force_update)

    async def rosters(
        self,
        season: int,
        force_update: bool = False,
        *,
        concurrency_limit: int = 5,
    ) -> pl.DataFrame:
        """Fetch Retrosheet roster (.ROS) files for a given season."""
        gateway = RetrosheetGateway(self._client)

        async def _fetch_rosters() -> pl.DataFrame:
            files = await gateway.get_season_contents(season)
            ros_files = [f for f in files if f.endswith(".ROS")]
            if not ros_files:
                raise ServerError(f"Rosters not available for {season}")

            async def _fetch_one_roster(filename: str) -> pl.DataFrame:
                team = filename[:3]
                raw_text = await gateway.get_roster_file(season, team)
                return parse_roster_csv(raw_text)

            tasks = [lambda f=f: _fetch_one_roster(f) for f in ros_files]
            dfs = await bounded_gather(tasks, concurrency_limit=concurrency_limit)
            valid_dfs = [df for df in dfs if df is not None and df.height > 0]
            if not valid_dfs:
                return empty_rosters_frame()

            return pl.concat(valid_dfs)

        key = generate_cache_key("retrosheet/rosters", {"season": season})
        return await self._client.cache.get_or_fetch(key, _fetch_rosters, force_update=force_update)

    async def park_codes(self, force_update: bool = False) -> pl.DataFrame:
        """Fetch Retrosheet park code reference data."""

        async def _fetch() -> pl.DataFrame:
            raw_text = await RetrosheetGateway(self._client).get_park_codes_csv()
            return parse_park_codes_csv(raw_text)

        key = generate_cache_key("retrosheet/park_codes", {})
        return await self._client.cache.get_or_fetch(key, _fetch, force_update=force_update)

    async def schedules(self, season: int, force_update: bool = False) -> pl.DataFrame:
        """Fetch Retrosheet schedule CSV for a given season."""
        gateway = RetrosheetGateway(self._client)

        async def _fetch() -> pl.DataFrame:
            files = await gateway.get_season_contents(season)
            file_name = f"{season}schedule.csv"
            if file_name not in files:
                raise ServerError(f"Schedule not available for {season}")

            raw_text = await gateway.get_schedule_csv(season)
            return parse_schedule_csv(raw_text)

        key = generate_cache_key("retrosheet/schedules", {"season": season})
        return await self._client.cache.get_or_fetch(key, _fetch, force_update=force_update)

    async def season_game_logs(self, season: int, force_update: bool = False) -> pl.DataFrame:
        """Fetch Retrosheet season game logs (GL{season}.TXT) for a given season."""
        gateway = RetrosheetGateway(self._client)

        async def _fetch() -> pl.DataFrame:
            files = await gateway.get_season_contents(season)
            gamelog_file_name = f"GL{season}.TXT"
            if gamelog_file_name not in files:
                raise ServerError(f"Season game logs not available for {season}")

            raw_text = await gateway.get_season_gamelog_csv(season)
            return parse_gamelog_csv(raw_text)

        key = generate_cache_key("retrosheet/season_game_logs", {"season": season})
        return await self._client.cache.get_or_fetch(key, _fetch, force_update=force_update)

    async def _get_gamelog_generic(self, suffix: str, force_update: bool = False) -> pl.DataFrame:
        async def _fetch() -> pl.DataFrame:
            raw_text = await RetrosheetGateway(self._client).get_gamelog_csv(suffix)
            return parse_gamelog_csv(raw_text)

        key = generate_cache_key(f"retrosheet/gamelog/{suffix}", {})
        return await self._client.cache.get_or_fetch(key, _fetch, force_update=force_update)

    async def world_series_logs(self, force_update: bool = False) -> pl.DataFrame:
        """Fetch Retrosheet World Series game logs."""
        return await self._get_gamelog_generic("WS", force_update=force_update)

    async def all_star_game_logs(self, force_update: bool = False) -> pl.DataFrame:
        """Fetch Retrosheet All-Star Game logs."""
        return await self._get_gamelog_generic("AS", force_update=force_update)

    async def wild_card_logs(self, force_update: bool = False) -> pl.DataFrame:
        """Fetch Retrosheet Wild Card game logs."""
        return await self._get_gamelog_generic("WC", force_update=force_update)

    async def division_series_logs(self, force_update: bool = False) -> pl.DataFrame:
        """Fetch Retrosheet Division Series game logs."""
        return await self._get_gamelog_generic("DV", force_update=force_update)

    async def lcs_logs(self, force_update: bool = False) -> pl.DataFrame:
        """Fetch Retrosheet League Championship Series game logs."""
        return await self._get_gamelog_generic("LC", force_update=force_update)


def __getattr__(name: str) -> None:
    raise AttributeError(
        f"Top-level function 'polars_baseball.retrosheet.{name}' was removed. "
        f"Use BaseballClient: `client = BaseballClient(); await client.retrosheet.{name}(...)`."
    )


__all__ = ["RetrosheetClient"]
