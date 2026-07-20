import asyncio
from collections.abc import Awaitable, Callable, Mapping, Sequence

import polars as pl

from polars_baseball._config import SAVANT_GAMEFEED_URL
from polars_baseball.context import BaseballContext
from polars_baseball.exceptions import InvalidParameterError
from polars_baseball.gateways.savant import SavantGateway
from polars_baseball.parsers.savant_gamefeed import EXIT_VELOCITY_SCHEMA, PITCH_DATA_SCHEMA, SavantGamefeedParser

_EXIT_VELOCITY_DATASET = "exit_velocity"
_PITCH_DATA_DATASET = "pitch_data"


def _validate_game_pk(game_pk: int | str) -> int:
    if isinstance(game_pk, int) and not isinstance(game_pk, bool):
        return game_pk
    if isinstance(game_pk, str) and game_pk.strip().isdigit():
        return int(game_pk.strip())
    raise InvalidParameterError(f"game_pk must be an integer or integer string, got {game_pk!r}")


async def savant_gamefeed_exit_velocity(
    game_pk: int | str,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch exit velocity data for a single game."""
    ctx = context or BaseballContext.default()
    parser = SavantGamefeedParser()
    return await SavantGateway(ctx).get_gamefeed_dataset(
        SAVANT_GAMEFEED_URL,
        _validate_game_pk(game_pk),
        _EXIT_VELOCITY_DATASET,
        parser.parse_exit_velocity,
    )


async def savant_gamefeed_pitch_data(
    game_pk: int | str,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch pitch-by-pitch data for a single game."""
    ctx = context or BaseballContext.default()
    parser = SavantGamefeedParser()
    return await SavantGateway(ctx).get_gamefeed_dataset(
        SAVANT_GAMEFEED_URL,
        _validate_game_pk(game_pk),
        _PITCH_DATA_DATASET,
        parser.parse_pitch_data,
    )


async def _fetch_many_gamefeed(
    game_pks: Sequence[int | str],
    single_fetcher: Callable[[int | str, BaseballContext | None], Awaitable[pl.DataFrame]],
    empty_schema: Mapping[str, pl.DataType | type[pl.DataType]],
    context: BaseballContext | None = None,
    parallel: bool = True,
) -> pl.DataFrame:
    if not game_pks:
        return pl.DataFrame(schema=empty_schema)

    ctx = context or BaseballContext.default()
    validated = [_validate_game_pk(pk) for pk in game_pks]
    tasks = [single_fetcher(pk, ctx) for pk in validated]

    dfs = await asyncio.gather(*tasks) if parallel else [await t for t in tasks]
    return pl.concat(dfs, how="diagonal")


async def savant_gamefeed_exit_velocity_many(
    game_pks: Sequence[int | str],
    context: BaseballContext | None = None,
    parallel: bool = True,
) -> pl.DataFrame:
    """Fetch exit velocity data for multiple games."""
    return await _fetch_many_gamefeed(game_pks, savant_gamefeed_exit_velocity, EXIT_VELOCITY_SCHEMA, context, parallel)


async def savant_gamefeed_pitch_data_many(
    game_pks: Sequence[int | str],
    context: BaseballContext | None = None,
    parallel: bool = True,
) -> pl.DataFrame:
    """Fetch pitch-by-pitch data for multiple games."""
    return await _fetch_many_gamefeed(game_pks, savant_gamefeed_pitch_data, PITCH_DATA_SCHEMA, context, parallel)
