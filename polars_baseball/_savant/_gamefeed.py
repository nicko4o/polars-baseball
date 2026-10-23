"""Baseball Savant gamefeed exit velocity and pitch data mixin."""

from __future__ import annotations

from collections.abc import Awaitable, Callable, Mapping, Sequence
from typing import TYPE_CHECKING

import polars as pl

from polars_baseball._concurrency import bounded_gather
from polars_baseball._config import (
    DEFAULT_GAMEFEED_CONCURRENCY_LIMIT,
    SAVANT_GAMEFEED_URL,
)
from polars_baseball._savant._statcast import _validate_game_pk
from polars_baseball.parsers.savant_gamefeed import (
    EXIT_VELOCITY_SCHEMA,
    PITCH_DATA_SCHEMA,
    SavantGamefeedParser,
)

if TYPE_CHECKING:
    from polars_baseball.gateways.savant import SavantGateway

_EXIT_VELOCITY_DATASET = "exit_velocity"
_PITCH_DATA_DATASET = "pitch_data"


class SavantGamefeedMixin:
    """Methods for Savant live and post-game gamefeed data."""

    _gateway: SavantGateway

    async def gamefeed_exit_velocity(self, game_pk: int | str) -> pl.DataFrame:
        """Fetch exit velocity data for a single game."""
        parser = SavantGamefeedParser()
        return await self._gateway.get_gamefeed_dataset(
            SAVANT_GAMEFEED_URL,
            _validate_game_pk(game_pk),
            _EXIT_VELOCITY_DATASET,
            parser.parse_exit_velocity,
        )

    async def gamefeed_pitch_data(self, game_pk: int | str) -> pl.DataFrame:
        """Fetch pitch-by-pitch data for a single game."""
        parser = SavantGamefeedParser()
        return await self._gateway.get_gamefeed_dataset(
            SAVANT_GAMEFEED_URL,
            _validate_game_pk(game_pk),
            _PITCH_DATA_DATASET,
            parser.parse_pitch_data,
        )

    async def _fetch_many_gamefeed(
        self,
        game_pks: Sequence[int | str],
        single_fetcher: Callable[[int], Awaitable[pl.DataFrame]],
        empty_schema: Mapping[str, pl.DataType | type[pl.DataType]],
        parallel: bool = True,
        concurrency_limit: int = DEFAULT_GAMEFEED_CONCURRENCY_LIMIT,
    ) -> pl.DataFrame:
        if not game_pks:
            return pl.DataFrame(schema=empty_schema)
        validated = [_validate_game_pk(pk) for pk in game_pks]
        effective_limit = concurrency_limit if parallel else 1
        tasks = [lambda pk=pk: single_fetcher(pk) for pk in validated]
        dfs: list[pl.DataFrame] = await bounded_gather(tasks, concurrency_limit=effective_limit)
        return pl.concat(dfs, how="diagonal")

    async def gamefeed_exit_velocity_many(
        self,
        game_pks: Sequence[int | str],
        parallel: bool = True,
        concurrency_limit: int = DEFAULT_GAMEFEED_CONCURRENCY_LIMIT,
    ) -> pl.DataFrame:
        """Fetch exit velocity data for multiple games."""
        return await self._fetch_many_gamefeed(
            game_pks,
            self.gamefeed_exit_velocity,
            EXIT_VELOCITY_SCHEMA,
            parallel=parallel,
            concurrency_limit=concurrency_limit,
        )

    async def gamefeed_pitch_data_many(
        self,
        game_pks: Sequence[int | str],
        parallel: bool = True,
        concurrency_limit: int = DEFAULT_GAMEFEED_CONCURRENCY_LIMIT,
    ) -> pl.DataFrame:
        """Fetch pitch-by-pitch data for multiple games."""
        return await self._fetch_many_gamefeed(
            game_pks,
            self.gamefeed_pitch_data,
            PITCH_DATA_SCHEMA,
            parallel=parallel,
            concurrency_limit=concurrency_limit,
        )
