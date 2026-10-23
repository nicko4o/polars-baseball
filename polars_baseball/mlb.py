"""Namespaced client for MLB Stats API endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING

from polars_baseball._mlb import (
    FilmRoomQueryBuilder,
    MlbDraftTransactionsMixin,
    MlbFilmRoomMixin,
    MlbGameMixin,
    MlbPeopleMixin,
    MlbScheduleMixin,
    MlbStatsMixin,
    film_room_cache_key,
)
from polars_baseball.gateways.film_room import FilmRoomGateway
from polars_baseball.gateways.mlb import MlbStatsGateway

if TYPE_CHECKING:
    from polars_baseball.client import BaseballClient


class MlbClient(
    MlbGameMixin,
    MlbScheduleMixin,
    MlbPeopleMixin,
    MlbStatsMixin,
    MlbDraftTransactionsMixin,
    MlbFilmRoomMixin,
):
    """Namespaced MLB Stats API client."""

    def __init__(self, client: BaseballClient) -> None:
        self._client = client
        self._gateway = MlbStatsGateway(client)
        self._film_room_gateway = FilmRoomGateway(client)


__all__ = [
    "FilmRoomQueryBuilder",
    "MlbClient",
    "film_room_cache_key",
]
