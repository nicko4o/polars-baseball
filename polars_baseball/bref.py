"""Namespaced client for Baseball Reference endpoints."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

import polars as pl

from polars_baseball._schemas.bref import (
    BWAR_BAT_REQUIRED,
    BWAR_BAT_TYPES,
    BWAR_PITCH_REQUIRED,
    BWAR_PITCH_TYPES,
)
from polars_baseball.exceptions import InvalidParameterError
from polars_baseball.gateways.bref import BRefGateway

if TYPE_CHECKING:
    from polars_baseball.client import BaseballClient


class BRefClient:
    """Namespaced Baseball Reference client."""

    def __init__(self, client: BaseballClient) -> None:
        self._client = client
        self._gateway = BRefGateway(client)

    async def _bwar_generic(
        self,
        stat_type: Literal["bat", "pitch"],
        required_cols: list[str],
        col_types: dict[str, pl.DataType | type[pl.DataType]],
        all_columns: bool = False,
    ) -> pl.DataFrame:
        return await self._gateway.get_bwar(stat_type, required_cols, col_types, all_columns=all_columns)

    async def bwar_bat(self, all_columns: bool = False) -> pl.DataFrame:
        """Fetch batting WAR from Baseball Reference."""
        return await self._bwar_generic("bat", BWAR_BAT_REQUIRED, BWAR_BAT_TYPES, all_columns=all_columns)

    async def bwar_pitch(self, all_columns: bool = False) -> pl.DataFrame:
        """Fetch pitching WAR from Baseball Reference."""
        return await self._bwar_generic("pitch", BWAR_PITCH_REQUIRED, BWAR_PITCH_TYPES, all_columns=all_columns)

    async def game_logs(
        self,
        player_id: str,
        year: int,
        log_type: Literal["batting", "pitching"] = "batting",
    ) -> pl.DataFrame:
        """Fetch Baseball Reference single-season game logs for a player."""
        if not player_id:
            raise InvalidParameterError("player_id must not be empty.")
        if log_type not in ("batting", "pitching"):
            raise InvalidParameterError("log_type must be either 'batting' or 'pitching'.")
        return await self._gateway.get_game_logs(player_id, year, log_type)

    async def splits(
        self,
        player_id: str,
        year: int | None = None,
        pitching: bool = False,
    ) -> list[pl.DataFrame]:
        """Fetch Baseball Reference platoon/situational splits for a player."""
        if not player_id:
            raise InvalidParameterError("player_id must not be empty.")
        df_main, player_info, df_level = await self._gateway.get_splits(player_id, year, pitching)
        df_info = pl.DataFrame(
            {
                "Position": [player_info.get("Position", "")],
                "Bats": [player_info.get("Bats", "")],
                "Throws": [player_info.get("Throws", "")],
            }
        )
        return [df_main, df_info, df_level]


__all__ = ["BRefClient"]
