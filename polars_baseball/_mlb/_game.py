"""MLB game data mixin (boxscore, linescore, play-by-play, live feed, highlights)."""

from __future__ import annotations

from datetime import timedelta
from typing import TYPE_CHECKING

import polars as pl

from polars_baseball._cache import generate_cache_key
from polars_baseball._mlb_contracts import (
    MLB_CACHE_MAX_AGE,
    MLB_LIVE_ENDPOINT_CACHE_MAX_AGE,
    boxscore_url,
    game_content_url,
    linescore_url,
    live_feed_url,
    play_by_play_url,
    win_probability_url,
)
from polars_baseball.exceptions import InvalidParameterError
from polars_baseball.parsers.mlb import (
    parse_mlb_boxscore,
    parse_mlb_boxscore_stats,
    parse_mlb_game_feed_live,
    parse_mlb_game_highlights,
    parse_mlb_game_linescore,
    parse_mlb_play_by_play,
    parse_mlb_win_probability,
)

if TYPE_CHECKING:
    from polars_baseball.client import BaseballClient
    from polars_baseball.gateways.mlb import MlbStatsGateway


class MlbGameMixin:
    """Methods for retrieving MLB game-level data."""

    _client: BaseballClient
    _gateway: MlbStatsGateway

    async def game_boxscore(self, game_pk: int, force_update: bool = False) -> pl.DataFrame:
        """Fetch MLB game boxscore."""
        if game_pk <= 0:
            raise InvalidParameterError("game_pk must be a positive integer.")
        url = boxscore_url(game_pk)
        return await self._gateway.fetch(
            url,
            None,
            "Failed to fetch or parse MLB game boxscore",
            lambda d: parse_mlb_boxscore(d, game_pk),
            use_cache=True,
            max_age=MLB_CACHE_MAX_AGE,
            force_update=force_update,
        )

    async def game_boxscore_stats(self, game_pk: int, force_update: bool = False) -> pl.DataFrame:
        """Fetch MLB game boxscore stats."""
        if game_pk <= 0:
            raise InvalidParameterError("game_pk must be a positive integer.")
        url = boxscore_url(game_pk)
        key = generate_cache_key(url, {"schema": "stats"})
        return await self._gateway.fetch(
            url,
            None,
            "Failed to fetch or parse MLB game boxscore stats",
            lambda d: parse_mlb_boxscore_stats(d, game_pk),
            use_cache=True,
            max_age=MLB_CACHE_MAX_AGE,
            force_update=force_update,
            cache_key=key,
        )

    async def game_linescore(
        self,
        game_pk: int,
        force_update: bool = False,
        cache_max_age: timedelta | None = MLB_LIVE_ENDPOINT_CACHE_MAX_AGE,
    ) -> pl.DataFrame:
        """Fetch MLB game linescore."""
        if game_pk <= 0:
            raise InvalidParameterError("game_pk must be a positive integer.")
        url = linescore_url(game_pk)
        return await self._gateway.fetch(
            url,
            None,
            "Failed to fetch or parse MLB game linescore",
            lambda d: parse_mlb_game_linescore(d, game_pk),
            use_cache=True,
            max_age=cache_max_age,
            force_update=force_update,
        )

    async def game_play_by_play(
        self,
        game_pk: int,
        win_probability: bool = False,
        force_update: bool = False,
    ) -> pl.DataFrame:
        """Fetch MLB game play-by-play events."""
        if game_pk <= 0:
            raise InvalidParameterError("game_pk must be a positive integer.")
        if win_probability:
            url = win_probability_url(game_pk)
            return await self._gateway.fetch_payload(
                url,
                None,
                "Failed to fetch or parse MLB win probability data",
                lambda d: parse_mlb_win_probability(d, game_pk),
                use_cache=True,
                max_age=MLB_CACHE_MAX_AGE,
                force_update=force_update,
            )
        url = play_by_play_url(game_pk)
        return await self._gateway.fetch(
            url,
            None,
            "Failed to fetch or parse MLB game play-by-play",
            lambda d: parse_mlb_play_by_play(d, game_pk),
            use_cache=True,
            max_age=MLB_CACHE_MAX_AGE,
            force_update=force_update,
        )

    async def game_win_probability(self, game_pk: int, force_update: bool = False) -> pl.DataFrame:
        """Fetch MLB game win probability."""
        if game_pk <= 0:
            raise InvalidParameterError("game_pk must be a positive integer.")
        return await self.game_play_by_play(game_pk=game_pk, win_probability=True, force_update=force_update)

    async def game_feed_live(self, game_pk: int, force_update: bool = False) -> pl.DataFrame:
        """Fetch MLB live game feed."""
        if game_pk <= 0:
            raise InvalidParameterError("game_pk must be a positive integer.")
        url = live_feed_url(game_pk)
        return await self._gateway.fetch(
            url,
            None,
            "Failed to fetch or parse MLB live feed",
            lambda d: parse_mlb_game_feed_live(d, game_pk),
            use_cache=True,
            max_age=MLB_LIVE_ENDPOINT_CACHE_MAX_AGE,
            force_update=force_update,
        )

    async def game_highlights(self, game_pk: int, force_update: bool = False) -> pl.DataFrame:
        """Fetch MLB game highlights."""
        if game_pk <= 0:
            raise InvalidParameterError("game_pk must be a positive integer.")
        url = game_content_url(game_pk)
        return await self._gateway.fetch(
            url,
            None,
            "Failed to fetch or parse MLB game highlights",
            lambda d: parse_mlb_game_highlights(d, game_pk),
            use_cache=True,
            max_age=MLB_CACHE_MAX_AGE,
            force_update=force_update,
        )
