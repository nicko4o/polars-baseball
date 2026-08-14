from datetime import datetime
from typing import cast

import polars as pl

from polars_baseball._cache import cached, generate_cache_key
from polars_baseball._config import FILM_ROOM_GRAPHQL_URL
from polars_baseball.apis.mlb._contracts import MLB_CACHE_MAX_AGE
from polars_baseball.context import BaseballContext
from polars_baseball.exceptions import InvalidParameterError
from polars_baseball.gateways.film_room import FilmRoomGateway
from polars_baseball.parsers.film_room import parse_film_room_search


def _build_int_clause(field: str, val: list[int] | int | None) -> str | None:
    if val is None:
        return None
    v_list = [val] if isinstance(val, int) else val
    if not v_list:
        return None
    ids_str = ", ".join(str(i) for i in v_list)
    return f"{field} = [{ids_str}]"


def _build_str_clause(field: str, val: list[str] | str | None) -> str | None:
    if val is None:
        return None
    v_list = [val] if isinstance(val, str) else val
    if not v_list:
        return None
    escaped_strs = [s.replace('"', '\\"') for s in v_list]
    strs = ", ".join(f'"{s}"' for s in escaped_strs)
    return f"{field} = [{strs}]"


def _build_range_clauses(
    min_ev: float | None,
    max_ev: float | None,
    min_dist: int | None,
    max_dist: int | None,
) -> list[str]:
    res: list[str] = []
    if min_ev is not None:
        res.append(f"ExitVelocity >= {min_ev}")
    if max_ev is not None:
        res.append(f"ExitVelocity <= {max_ev}")
    if min_dist is not None:
        res.append(f"HitDistance >= {min_dist}")
    if max_dist is not None:
        res.append(f"HitDistance <= {max_dist}")
    return res


def _validate_non_empty_param(name: str, val: object) -> None:
    if val is not None:
        if isinstance(val, (list, tuple)) and len(val) == 0:
            raise InvalidParameterError(f"{name} cannot be an empty sequence")
        if isinstance(val, str) and not val.strip():
            raise InvalidParameterError(f"{name} cannot be an empty string")


def _validate_film_room_params(
    player_ids: list[int] | int | None,
    team_ids: list[int] | int | None,
    seasons: list[int] | int | None,
    date_range: tuple[str, str] | None,
    event_types: list[str] | str | None,
    pitch_types: list[str] | str | None,
    min_exit_velocity: float | None,
    max_exit_velocity: float | None,
    min_distance: int | None,
    max_distance: int | None,
    limit: int,
    query: str | None = None,
) -> None:
    if limit <= 0:
        raise InvalidParameterError(f"limit must be greater than 0, got {limit}")

    _validate_non_empty_param("player_ids", player_ids)
    _validate_non_empty_param("team_ids", team_ids)
    _validate_non_empty_param("seasons", seasons)
    _validate_non_empty_param("event_types", event_types)
    _validate_non_empty_param("pitch_types", pitch_types)
    _validate_non_empty_param("query", query)

    if date_range is not None:
        if len(date_range) != 2:
            raise InvalidParameterError(f"date_range must be a tuple of (start_date, end_date), got {date_range}")
        try:
            d_start = datetime.strptime(date_range[0], "%Y-%m-%d").date()
            d_end = datetime.strptime(date_range[1], "%Y-%m-%d").date()
        except ValueError as exc:
            raise InvalidParameterError(f"date_range dates must be in 'YYYY-MM-DD' format, got {date_range}") from exc
        if d_start > d_end:
            raise InvalidParameterError(f"start_date ({date_range[0]}) cannot be after end_date ({date_range[1]})")

    if min_exit_velocity is not None and max_exit_velocity is not None and min_exit_velocity > max_exit_velocity:
        raise InvalidParameterError(
            f"min_exit_velocity ({min_exit_velocity}) cannot exceed max_exit_velocity ({max_exit_velocity})"
        )

    if min_distance is not None and max_distance is not None and min_distance > max_distance:
        raise InvalidParameterError(f"min_distance ({min_distance}) cannot exceed max_distance ({max_distance})")


class FilmRoomQueryBuilder:
    """Builder for constructing MLB Film Room search query strings."""

    @staticmethod
    def build(
        *,
        player_ids: list[int] | int | None = None,
        team_ids: list[int] | int | None = None,
        seasons: list[int] | int | None = None,
        date_range: tuple[str, str] | None = None,
        event_types: list[str] | str | None = None,
        pitch_types: list[str] | str | None = None,
        min_exit_velocity: float | None = None,
        max_exit_velocity: float | None = None,
        min_distance: int | None = None,
        max_distance: int | None = None,
        query: str | None = None,
    ) -> str:
        """Build structured query string for MLB Film Room."""
        if query is not None and query.strip():
            return query.strip()

        clauses: list[str] = []

        for c in (
            _build_int_clause("PlayerID", player_ids),
            _build_int_clause("TeamID", team_ids),
            _build_int_clause("Season", seasons),
            f'Date = ["{date_range[0]}", "{date_range[1]}"]' if (date_range and len(date_range) == 2) else None,
            _build_str_clause("HitResult", event_types),
            _build_str_clause("PitchType", pitch_types),
        ):
            if c:
                clauses.append(c)

        clauses.extend(_build_range_clauses(min_exit_velocity, max_exit_velocity, min_distance, max_distance))

        base_query = " AND ".join(clauses) if clauses else 'ContentTags = ["home-run"]'
        return f"{base_query} Order By Timestamp DESC"


def film_room_cache_key(**kw: object) -> str:
    """Generate MD5 cache key for film_room_search endpoint."""
    limit = cast(int, kw.get("limit", 100))
    query_str = FilmRoomQueryBuilder.build(
        player_ids=cast(list[int] | int | None, kw.get("player_ids")),
        team_ids=cast(list[int] | int | None, kw.get("team_ids")),
        seasons=cast(list[int] | int | None, kw.get("seasons")),
        date_range=cast(tuple[str, str] | None, kw.get("date_range")),
        event_types=cast(list[str] | str | None, kw.get("event_types")),
        pitch_types=cast(list[str] | str | None, kw.get("pitch_types")),
        min_exit_velocity=cast(float | None, kw.get("min_exit_velocity")),
        max_exit_velocity=cast(float | None, kw.get("max_exit_velocity")),
        min_distance=cast(int | None, kw.get("min_distance")),
        max_distance=cast(int | None, kw.get("max_distance")),
        query=cast(str | None, kw.get("query")),
    )
    return generate_cache_key(FILM_ROOM_GRAPHQL_URL, {"query": query_str, "limit": limit})


@cached(key=film_room_cache_key, max_age=MLB_CACHE_MAX_AGE)
async def mlb_film_room_search(
    *,
    player_ids: list[int] | int | None = None,
    team_ids: list[int] | int | None = None,
    seasons: list[int] | int | None = None,
    date_range: tuple[str, str] | None = None,
    event_types: list[str] | str | None = None,
    pitch_types: list[str] | str | None = None,
    min_exit_velocity: float | None = None,
    max_exit_velocity: float | None = None,
    min_distance: int | None = None,
    max_distance: int | None = None,
    limit: int = 100,
    query: str | None = None,
    force_update: bool = False,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Search MLB Film Room for video clips matching criteria.

    Args:
        player_ids: MLB player ID or list of player IDs.
        team_ids: MLB team ID or list of team IDs.
        seasons: Season year or list of season years.
        date_range: Date range tuple (start_date, end_date).
        event_types: Event type or list of event types.
        pitch_types: Pitch code or list of pitch codes.
        min_exit_velocity: Minimum exit velocity in mph.
        max_exit_velocity: Maximum exit velocity in mph.
        min_distance: Minimum hit distance in feet.
        max_distance: Maximum hit distance in feet.
        limit: Maximum number of video clips to return.
        query: Raw MLB Film Room search query string.
        force_update: If True, ignore cached data.
        context: Execution context providing HTTP client and cache configuration.

    Returns:
        pl.DataFrame: DataFrame containing structured video clip search results.
    """
    _validate_film_room_params(
        player_ids=player_ids,
        team_ids=team_ids,
        seasons=seasons,
        date_range=date_range,
        event_types=event_types,
        pitch_types=pitch_types,
        min_exit_velocity=min_exit_velocity,
        max_exit_velocity=max_exit_velocity,
        min_distance=min_distance,
        max_distance=max_distance,
        limit=limit,
        query=query,
    )

    query_str = FilmRoomQueryBuilder.build(
        player_ids=player_ids,
        team_ids=team_ids,
        seasons=seasons,
        date_range=date_range,
        event_types=event_types,
        pitch_types=pitch_types,
        min_exit_velocity=min_exit_velocity,
        max_exit_velocity=max_exit_velocity,
        min_distance=min_distance,
        max_distance=max_distance,
        query=query,
    )

    ctx = context or BaseballContext.default()
    return await FilmRoomGateway(ctx).fetch_search(
        query_str=query_str,
        limit=limit,
        error_msg="Failed to fetch or parse MLB Film Room search results",
        parser=parse_film_room_search,
    )


film_room_search = mlb_film_room_search
