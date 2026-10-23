"""MLB Film Room GraphQL query builder and search mixin."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import date, datetime
from typing import TYPE_CHECKING, cast

import polars as pl

from polars_baseball._cache import generate_cache_key
from polars_baseball._config import FILM_ROOM_GRAPHQL_URL
from polars_baseball._mlb_contracts import MLB_CACHE_MAX_AGE
from polars_baseball.exceptions import InvalidParameterError
from polars_baseball.parsers.film_room import parse_film_room_search

if TYPE_CHECKING:
    from polars_baseball.client import BaseballClient
    from polars_baseball.gateways.film_room import FilmRoomGateway


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


def _normalize_date_str(val: str | date | datetime, field_name: str) -> str:
    if isinstance(val, date):
        return val.strftime("%Y-%m-%d")
    if isinstance(val, str):
        cleaned = val.strip().split("T")[0]
        try:
            datetime.strptime(cleaned, "%Y-%m-%d")
            return cleaned
        except ValueError as exc:
            raise InvalidParameterError(f"{field_name} date must be in 'YYYY-MM-DD' format, got {val!r}") from exc
    raise InvalidParameterError(f"{field_name} date must be a str, date, or datetime, got {type(val).__name__}")


def _validate_date_range(date_range: Sequence[str | date | datetime] | None) -> tuple[str, str] | None:
    if date_range is None:
        return None
    if len(date_range) != 2:
        raise InvalidParameterError(f"date_range must be a tuple of (start_date, end_date), got {date_range}")
    start_str = _normalize_date_str(date_range[0], "start_date")
    end_str = _normalize_date_str(date_range[1], "end_date")
    if start_str > end_str:
        raise InvalidParameterError(f"start_date ({start_str}) cannot be after end_date ({end_str})")
    return (start_str, end_str)


def _validate_non_empty_param(name: str, val: object) -> None:
    if val is not None:
        if isinstance(val, Sequence) and not isinstance(val, (str, bytes)) and len(val) == 0:
            raise InvalidParameterError(f"{name} cannot be an empty sequence")
        if isinstance(val, str) and not val.strip():
            raise InvalidParameterError(f"{name} cannot be an empty string")


@dataclass(frozen=True)
class FilmRoomSearchParams:
    """Encapsulates filter and pagination parameters for MLB Film Room searches."""

    player_ids: list[int] | int | None = None
    team_ids: list[int] | int | None = None
    seasons: list[int] | int | None = None
    date_range: Sequence[str | date | datetime] | None = None
    event_types: list[str] | str | None = None
    pitch_types: list[str] | str | None = None
    min_exit_velocity: float | None = None
    max_exit_velocity: float | None = None
    min_distance: int | None = None
    max_distance: int | None = None
    limit: int = 100
    query: str | None = None


def _validate_film_room_params(params: FilmRoomSearchParams) -> None:
    if params.limit <= 0:
        raise InvalidParameterError(f"limit must be greater than 0, got {params.limit}")

    _validate_non_empty_param("player_ids", params.player_ids)
    _validate_non_empty_param("team_ids", params.team_ids)
    _validate_non_empty_param("seasons", params.seasons)
    _validate_non_empty_param("event_types", params.event_types)
    _validate_non_empty_param("pitch_types", params.pitch_types)
    _validate_non_empty_param("query", params.query)

    _validate_date_range(params.date_range)

    if (
        params.min_exit_velocity is not None
        and params.max_exit_velocity is not None
        and params.min_exit_velocity > params.max_exit_velocity
    ):
        raise InvalidParameterError(
            f"min_exit_velocity ({params.min_exit_velocity}) cannot exceed max_exit_velocity ({params.max_exit_velocity})"
        )

    if (
        params.min_distance is not None
        and params.max_distance is not None
        and params.min_distance > params.max_distance
    ):
        raise InvalidParameterError(
            f"min_distance ({params.min_distance}) cannot exceed max_distance ({params.max_distance})"
        )


class FilmRoomQueryBuilder:
    """Builder for constructing MLB Film Room search query strings."""

    @staticmethod
    def build_from_params(params: FilmRoomSearchParams) -> str:
        if params.query is not None and params.query.strip():
            return params.query.strip()

        norm_dates = _validate_date_range(params.date_range)
        clauses: list[str] = []

        for c in (
            _build_int_clause("PlayerID", params.player_ids),
            _build_int_clause("TeamID", params.team_ids),
            _build_int_clause("Season", params.seasons),
            f'Date = ["{norm_dates[0]}", "{norm_dates[1]}"]' if norm_dates else None,
            _build_str_clause("HitResult", params.event_types),
            _build_str_clause("PitchType", params.pitch_types),
        ):
            if c:
                clauses.append(c)

        clauses.extend(
            _build_range_clauses(
                params.min_exit_velocity,
                params.max_exit_velocity,
                params.min_distance,
                params.max_distance,
            )
        )
        base_query = " AND ".join(clauses) if clauses else 'ContentTags = ["home-run"]'
        return f"{base_query} Order By Timestamp DESC"

    @staticmethod
    def build(
        *,
        player_ids: list[int] | int | None = None,
        team_ids: list[int] | int | None = None,
        seasons: list[int] | int | None = None,
        date_range: Sequence[str | date | datetime] | None = None,
        event_types: list[str] | str | None = None,
        pitch_types: list[str] | str | None = None,
        min_exit_velocity: float | None = None,
        max_exit_velocity: float | None = None,
        min_distance: int | None = None,
        max_distance: int | None = None,
        query: str | None = None,
    ) -> str:
        params = FilmRoomSearchParams(
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
        return FilmRoomQueryBuilder.build_from_params(params)


def film_room_cache_key(**kw: object) -> str:
    """Generate MD5 cache key for film_room_search endpoint."""
    limit = cast(int, kw.get("limit", 100))
    params = FilmRoomSearchParams(
        player_ids=cast(list[int] | int | None, kw.get("player_ids")),
        team_ids=cast(list[int] | int | None, kw.get("team_ids")),
        seasons=cast(list[int] | int | None, kw.get("seasons")),
        date_range=cast(Sequence[str | date | datetime] | None, kw.get("date_range")),
        event_types=cast(list[str] | str | None, kw.get("event_types")),
        pitch_types=cast(list[str] | str | None, kw.get("pitch_types")),
        min_exit_velocity=cast(float | None, kw.get("min_exit_velocity")),
        max_exit_velocity=cast(float | None, kw.get("max_exit_velocity")),
        min_distance=cast(int | None, kw.get("min_distance")),
        max_distance=cast(int | None, kw.get("max_distance")),
        limit=limit,
        query=cast(str | None, kw.get("query")),
    )
    query_str = FilmRoomQueryBuilder.build_from_params(params)
    return generate_cache_key(FILM_ROOM_GRAPHQL_URL, {"query": query_str, "limit": limit})


class MlbFilmRoomMixin:
    """Methods for searching MLB Film Room video highlights via GraphQL."""

    _client: BaseballClient
    _film_room_gateway: FilmRoomGateway

    async def film_room_search(
        self,
        *,
        player_ids: list[int] | int | None = None,
        team_ids: list[int] | int | None = None,
        seasons: list[int] | int | None = None,
        date_range: Sequence[str | date | datetime] | None = None,
        event_types: list[str] | str | None = None,
        pitch_types: list[str] | str | None = None,
        min_exit_velocity: float | None = None,
        max_exit_velocity: float | None = None,
        min_distance: int | None = None,
        max_distance: int | None = None,
        limit: int = 100,
        query: str | None = None,
        force_update: bool = False,
    ) -> pl.DataFrame:
        """Search MLB Film Room for video clips matching criteria."""
        params = FilmRoomSearchParams(
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
        _validate_film_room_params(params)
        return await self._film_room_gateway.fetch_search(
            query_str=FilmRoomQueryBuilder.build_from_params(params),
            limit=limit,
            error_msg="Failed to fetch or parse MLB Film Room search results",
            parser=parse_film_room_search,
            use_cache=True,
            max_age=MLB_CACHE_MAX_AGE,
            force_update=force_update,
        )
