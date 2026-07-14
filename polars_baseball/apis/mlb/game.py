import json
from datetime import timedelta

import polars as pl

from polars_baseball._cache import cached
from polars_baseball._schema_utils import validate_and_cast_schema
from polars_baseball._schemas.mlb import (
    MLB_BOXSCORE_REQUIRED,
    MLB_BOXSCORE_STATS_TYPES,
    MLB_BOXSCORE_TYPES,
    MLB_LINESCORE_REQUIRED,
    MLB_LINESCORE_TYPES,
    MLB_LIVE_FEED_REQUIRED,
    MLB_LIVE_FEED_TYPES,
    MLB_PBP_REQUIRED,
    MLB_PBP_TYPES,
)
from polars_baseball.apis.mlb._contracts import (
    MLB_CACHE_MAX_AGE,
    MLB_LIVE_ENDPOINT_CACHE_MAX_AGE,
    JsonObject,
    boxscore_cache_key,
    boxscore_stats_cache_key,
    boxscore_url,
    linescore_cache_key,
    linescore_url,
    live_feed_cache_key,
    live_feed_url,
    play_by_play_cache_key,
    play_by_play_url,
    win_probability_cache_key,
    win_probability_url,
)
from polars_baseball.context import BaseballContext, default_context
from polars_baseball.exceptions import InvalidParameterError, UpstreamParseError
from polars_baseball.gateways.mlb import MlbStatsGateway
from polars_baseball.parsers.mlb import (
    parse_boxscore,
    parse_linescore,
    parse_live_feed_pitch,
    parse_play,
)


def _parse_mlb_boxscore(data: JsonObject, game_pk: int) -> pl.DataFrame:
    rows = parse_boxscore(data, game_pk)
    if not rows:
        return pl.DataFrame()
    return validate_and_cast_schema(pl.DataFrame(rows), MLB_BOXSCORE_REQUIRED, MLB_BOXSCORE_TYPES)


def _parse_mlb_boxscore_stats(data: JsonObject, game_pk: int) -> pl.DataFrame:
    rows = parse_boxscore(data, game_pk)
    if not rows:
        return pl.DataFrame()
    return validate_and_cast_schema(pl.DataFrame(rows), MLB_BOXSCORE_REQUIRED, MLB_BOXSCORE_STATS_TYPES)


@cached(key=boxscore_cache_key, max_age=MLB_CACHE_MAX_AGE)
async def _fetch_mlb_game_boxscore(
    game_pk: int,
    force_update: bool = False,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    url = boxscore_url(game_pk)
    ctx = context or default_context()
    return await MlbStatsGateway(ctx).fetch(
        url, None, "Failed to fetch or parse MLB game boxscore", lambda d: _parse_mlb_boxscore(d, game_pk)
    )


@cached(key=boxscore_stats_cache_key, max_age=MLB_CACHE_MAX_AGE)
async def _fetch_mlb_game_boxscore_stats(
    game_pk: int,
    force_update: bool = False,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    url = boxscore_url(game_pk)
    ctx = context or default_context()
    return await MlbStatsGateway(ctx).fetch(
        url, None, "Failed to fetch or parse MLB game boxscore stats", lambda d: _parse_mlb_boxscore_stats(d, game_pk)
    )


async def mlb_game_boxscore(
    game_pk: int,
    force_update: bool = False,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch boxscore data for a single game from the MLB Stats API."""
    if game_pk <= 0:
        raise InvalidParameterError("game_pk must be a positive integer.")

    return await _fetch_mlb_game_boxscore(
        game_pk=game_pk,
        force_update=force_update,
        context=context,
    )


async def mlb_game_boxscore_stats(
    game_pk: int,
    force_update: bool = False,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch boxscore batting, pitching, and fielding stats for a single game."""
    if game_pk <= 0:
        raise InvalidParameterError("game_pk must be a positive integer.")

    return await _fetch_mlb_game_boxscore_stats(
        game_pk=game_pk,
        force_update=force_update,
        context=context,
    )


def _parse_mlb_play_by_play(data: JsonObject, game_pk: int) -> pl.DataFrame:
    all_plays = data.get("allPlays", [])
    if not all_plays:
        return pl.DataFrame()
    rows = [parse_play(p, game_pk) for p in all_plays]
    return validate_and_cast_schema(pl.DataFrame(rows), MLB_PBP_REQUIRED, MLB_PBP_TYPES)


@cached(key=play_by_play_cache_key, max_age=MLB_CACHE_MAX_AGE)
async def _fetch_mlb_game_play_by_play(
    game_pk: int,
    force_update: bool = False,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    url = play_by_play_url(game_pk)
    ctx = context or default_context()
    return await MlbStatsGateway(ctx).fetch(
        url, None, "Failed to fetch or parse MLB play-by-play data", lambda d: _parse_mlb_play_by_play(d, game_pk)
    )


@cached(key=win_probability_cache_key, max_age=MLB_CACHE_MAX_AGE)
async def _fetch_mlb_game_win_probability(
    game_pk: int,
    force_update: bool = False,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    url = win_probability_url(game_pk)
    ctx = context or default_context()
    try:
        raw_text = await ctx.http.get_text(url)
        data = json.loads(raw_text)
    except Exception as e:
        raise UpstreamParseError(f"Failed to fetch or parse MLB win probability data: {e}") from e

    if not isinstance(data, list):
        return pl.DataFrame()

    rows = [parse_play(p, game_pk) for p in data]
    if not rows:
        return pl.DataFrame()

    df = pl.DataFrame(rows)
    return validate_and_cast_schema(df, MLB_PBP_REQUIRED, MLB_PBP_TYPES)


async def mlb_game_play_by_play(
    game_pk: int,
    win_probability: bool = False,
    force_update: bool = False,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch play-by-play data for a game from MLB Stats API.

    Args:
        game_pk: MLB game ID.
        win_probability: If true, fetch from the winProbability endpoint,
            which includes per-play win probability, leverage index, and
            drama index fields.
        force_update: Bypass cache and fetch fresh data.
        context: Optional dependency injection context.
    """
    if game_pk <= 0:
        raise InvalidParameterError("game_pk must be a positive integer.")

    if win_probability:
        return await _fetch_mlb_game_win_probability(
            game_pk=game_pk,
            force_update=force_update,
            context=context,
        )

    return await _fetch_mlb_game_play_by_play(
        game_pk=game_pk,
        force_update=force_update,
        context=context,
    )


async def mlb_game_win_probability(
    game_pk: int,
    force_update: bool = False,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch per-play win probability and WPA data for an MLB game."""
    if game_pk <= 0:
        raise InvalidParameterError("game_pk must be a positive integer.")

    return await _fetch_mlb_game_win_probability(
        game_pk=game_pk,
        force_update=force_update,
        context=context,
    )


def _parse_mlb_game_feed_live(data: JsonObject, game_pk: int) -> pl.DataFrame:
    live_data = data.get("liveData", {})
    plays = live_data.get("plays", {})
    all_plays = plays.get("allPlays", [])

    rows = []
    for play in all_plays:
        play_events = play.get("playEvents", [])
        for event in play_events:
            if event.get("isPitch", False):
                rows.append(parse_live_feed_pitch(event, play, game_pk))

    if not rows:
        return pl.DataFrame()
    return validate_and_cast_schema(pl.DataFrame(rows), MLB_LIVE_FEED_REQUIRED, MLB_LIVE_FEED_TYPES)


@cached(key=live_feed_cache_key, max_age=MLB_CACHE_MAX_AGE)
async def _fetch_mlb_game_feed_live(
    game_pk: int,
    force_update: bool = False,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    url = live_feed_url(game_pk)
    ctx = context or default_context()
    return await MlbStatsGateway(ctx).fetch(
        url,
        {},
        "Failed to fetch or parse MLB game feed live data",
        lambda d: _parse_mlb_game_feed_live(d, game_pk),
    )


async def mlb_game_feed_live(
    game_pk: int,
    force_update: bool = False,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch MLB game live feed details (v1.1 endpoint) containing granular pitch data.

    Args:
        game_pk: The game's MLB ID (e.g. 715789).
        force_update: Bypass cache and fetch fresh data.
        context: Optional BaseballContext.
    """
    if game_pk <= 0:
        raise InvalidParameterError("game_pk must be a positive integer.")

    return await _fetch_mlb_game_feed_live(
        game_pk=game_pk,
        force_update=force_update,
        context=context,
    )


def _mlb_game_linescore_max_age(
    cache_max_age: timedelta | None = MLB_LIVE_ENDPOINT_CACHE_MAX_AGE,
    **kwargs: object,
) -> timedelta | None:
    return cache_max_age


def _parse_mlb_game_linescore(data: JsonObject, game_pk: int) -> pl.DataFrame:
    rows = parse_linescore(data, game_pk)
    if not rows:
        return pl.DataFrame()
    return validate_and_cast_schema(pl.DataFrame(rows), MLB_LINESCORE_REQUIRED, MLB_LINESCORE_TYPES)


@cached(key=linescore_cache_key, max_age=_mlb_game_linescore_max_age)
async def _fetch_mlb_game_linescore(
    game_pk: int,
    force_update: bool = False,
    cache_max_age: timedelta | None = MLB_LIVE_ENDPOINT_CACHE_MAX_AGE,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    url = linescore_url(game_pk)
    ctx = context or default_context()
    return await MlbStatsGateway(ctx).fetch(
        url,
        None,
        "Failed to fetch or parse MLB game linescore",
        lambda d: _parse_mlb_game_linescore(d, game_pk),
    )


async def mlb_game_linescore(
    game_pk: int,
    force_update: bool = False,
    cache_max_age: timedelta | None = MLB_LIVE_ENDPOINT_CACHE_MAX_AGE,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch inning-by-inning linescore data from the MLB Stats API.

    Args:
        game_pk: The game's MLB ID (e.g. 715789).
        force_update: Bypass cache and fetch fresh data.
        cache_max_age: Maximum cache age for this live-ish endpoint. Defaults
            to 10 seconds; pass a longer duration for completed games or
            ``force_update=True`` for a fresh fetch.
        context: Optional BaseballContext.
    """
    if game_pk <= 0:
        raise InvalidParameterError("game_pk must be a positive integer.")

    return await _fetch_mlb_game_linescore(
        game_pk=game_pk,
        force_update=force_update,
        cache_max_age=cache_max_age,
        context=context,
    )
