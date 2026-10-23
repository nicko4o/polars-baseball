"""Baseball Savant park factors mixin."""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

import polars as pl

from polars_baseball._concurrency import bounded_gather
from polars_baseball._config import (
    DEFAULT_STATCAST_CONCURRENCY_LIMIT,
    SAVANT_ROOT,
    STATCAST_PARK_FACTORS_START_YEAR,
)
from polars_baseball._season import most_recent_season
from polars_baseball.exceptions import InvalidParameterError
from polars_baseball.parsers.savant import parse_savant_park_factors

if TYPE_CHECKING:
    from polars_baseball.gateways.savant import SavantGateway

PATH_PARK_FACTORS = "/leaderboard/statcast-park-factors"


def _normalize_bat_side(bat_side: str) -> str:
    norm = str(bat_side).upper()
    if norm == "ALL":
        return "All"
    if norm in ("L", "R"):
        return norm
    raise InvalidParameterError("bat_side must be one of 'all', 'L', or 'R'.")


def _resolve_year_range(
    year: int | list[int] | tuple[int, int] | None,
    start_year: int | None,
    end_year: int | None,
) -> list[int]:
    if start_year is not None or end_year is not None:
        if start_year is None or end_year is None or not isinstance(start_year, int) or not isinstance(end_year, int):
            raise InvalidParameterError("Both start_year and end_year must be integers provided together.")
        if start_year > end_year:
            raise InvalidParameterError("start_year cannot be greater than end_year.")
        years = list(range(start_year, end_year + 1))
    elif isinstance(year, tuple):
        if len(year) != 2 or not isinstance(year[0], int) or not isinstance(year[1], int) or year[0] > year[1]:
            raise InvalidParameterError(
                "year tuple must be (start_year, end_year) with integer start_year <= end_year."
            )
        years = list(range(year[0], year[1] + 1))
    elif isinstance(year, list):
        if not year:
            raise InvalidParameterError("year list cannot be empty.")
        years = list(year)
    elif isinstance(year, int):
        years = [year]
    elif year is None:
        years = [most_recent_season()]
    else:
        raise InvalidParameterError(f"Invalid year specification: {year}")

    for yr in years:
        if not isinstance(yr, int) or yr < STATCAST_PARK_FACTORS_START_YEAR:
            raise InvalidParameterError(f"Year must be an integer >= {STATCAST_PARK_FACTORS_START_YEAR}.")
    return years


def _normalize_venue_ids(venue_id: int | list[int] | None) -> list[int] | None:
    if venue_id is None:
        return None
    if isinstance(venue_id, int):
        if venue_id <= 0:
            raise InvalidParameterError("venue_id must be a positive integer.")
        return [venue_id]
    if isinstance(venue_id, list):
        if not all(isinstance(v, int) and v > 0 for v in venue_id):
            raise InvalidParameterError("All venue_ids must be positive integers.")
        return list(venue_id)
    raise InvalidParameterError(f"Invalid venue_id specification: {type(venue_id).__name__}")


class SavantParkFactorsMixin:
    """Methods for Savant venue and park factor metrics."""

    _gateway: SavantGateway

    async def park_factors(
        self,
        year: int | list[int] | tuple[int, int] | None = None,
        start_year: int | None = None,
        end_year: int | None = None,
        venue_id: int | list[int] | None = None,
        bat_side: Literal["all", "L", "R"] = "all",
        concurrency_limit: int = DEFAULT_STATCAST_CONCURRENCY_LIMIT,
    ) -> pl.DataFrame:
        """Fetch Statcast Park Factors from Baseball Savant."""
        savant_bat_side = _normalize_bat_side(bat_side)
        years = _resolve_year_range(year, start_year, end_year)
        venue_ids = _normalize_venue_ids(venue_id)

        async def _fetch_yr(yr: int) -> pl.DataFrame:
            url = f"{SAVANT_ROOT}{PATH_PARK_FACTORS}"
            params = {"type": "year", "year": str(yr), "batSide": savant_bat_side}
            raw = await self._gateway.get_leaderboard(url, params)
            return parse_savant_park_factors(raw)

        tasks = [lambda yr=yr: _fetch_yr(yr) for yr in years]
        results = await bounded_gather(tasks, concurrency_limit=concurrency_limit)
        df = pl.concat(results, how="vertical") if results else pl.DataFrame()

        if venue_ids is not None and not df.is_empty():
            df = df.filter(pl.col("venue_id").is_in(venue_ids))
        return df
