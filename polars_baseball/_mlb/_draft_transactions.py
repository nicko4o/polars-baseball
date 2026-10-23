"""MLB draft, transactions, and prospect rankings mixin."""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING

import polars as pl

from polars_baseball._cache import generate_cache_key
from polars_baseball._config import (
    MILB_ROOT,
    MLB_FIRST_YEAR,
    MLB_ROOT,
    PROSPECT_RANKINGS_START_YEAR,
)
from polars_baseball._mlb._taxonomy import MlbTaxonomyMixin
from polars_baseball._mlb_contracts import (
    MLB_CACHE_MAX_AGE,
    MLB_DEFAULT_SPORT_ID,
    draft_url,
    transactions_url,
)
from polars_baseball._season import coerce_datestring, most_recent_season
from polars_baseball.exceptions import InvalidParameterError, UpstreamParseError
from polars_baseball.parsers.mlb import (
    MLBApiParser,
    parse_mlb_draft,
    parse_mlb_transactions,
)
from polars_baseball.parsers.pipeline import MLBPipelineParser

if TYPE_CHECKING:
    from polars_baseball.client import BaseballClient
    from polars_baseball.gateways.mlb import MlbStatsGateway

_VALID_PROSPECT_TYPES = frozenset({"batters", "pitchers"})


def _validate_date_format(val: str | None, name: str) -> None:
    if val is not None and not re.match(r"^\d{4}-\d{2}-\d{2}$", val):
        raise InvalidParameterError(f"Invalid format for parameter {name}. Must be YYYY-MM-DD.")


def _validate_id_param(val: int | None, name: str) -> None:
    if val is not None and val <= 0:
        raise InvalidParameterError(f"{name} must be a positive integer.")


@dataclass(frozen=True)
class TransactionsFilterParams:
    """Filter parameters for MLB transactions query."""

    date: str | None = None
    start_date: str | None = None
    end_date: str | None = None
    team_id: int | None = None
    player_id: int | None = None
    sport_id: int = MLB_DEFAULT_SPORT_ID

    def validate(self) -> None:
        has_any_filter = any(
            v is not None for v in (self.date, self.start_date, self.end_date, self.team_id, self.player_id)
        )
        if not has_any_filter:
            raise InvalidParameterError(
                "Must specify at least one filter: date, start_date/end_date, team_id, or player_id."
            )
        if self.date is not None and (self.start_date is not None or self.end_date is not None):
            raise InvalidParameterError("Provide either date or start_date/end_date, not both.")
        if self.sport_id <= 0:
            raise InvalidParameterError("sport_id must be a positive integer.")
        _validate_id_param(self.team_id, "team_id")
        _validate_id_param(self.player_id, "player_id")
        _validate_date_format(self.date, "date")
        _validate_date_format(self.start_date, "start_date")
        _validate_date_format(self.end_date, "end_date")

    def to_params(self) -> dict[str, object]:
        params: dict[str, object] = {"sportId": self.sport_id}
        if self.date:
            params["date"] = self.date
        if self.start_date:
            params["startDate"] = self.start_date
        if self.end_date:
            params["endDate"] = self.end_date
        if self.team_id is not None:
            params["teamId"] = self.team_id
        if self.player_id is not None:
            params["playerId"] = self.player_id
        return params


def _clean_prospect_df(df: pl.DataFrame) -> pl.DataFrame:
    sorted_df = df.sort("Rk") if "Rk" in df.columns else df
    drop_cols = [c for c in sorted_df.columns if "Tm" in c or "Unnamed" in c]
    if drop_cols:
        return sorted_df.drop(drop_cols)
    return sorted_df


def _extract_prospect_df(dfs: list[pl.DataFrame], player_type: str | None) -> pl.DataFrame:
    if not dfs:
        raise UpstreamParseError("MLB top prospects response did not contain prospect tables.")
    if player_type == "batters":
        return dfs[0]
    if player_type == "pitchers":
        if len(dfs) < 2:
            raise UpstreamParseError("MLB top prospects response did not contain a pitchers table.")
        return dfs[1]
    return pl.concat(dfs, how="diagonal")


class MlbDraftTransactionsMixin(MlbTaxonomyMixin):
    """Methods for retrieving MLB draft records, transactions, and prospect rankings."""

    _client: BaseballClient
    _gateway: MlbStatsGateway

    async def draft(
        self,
        year: int,
        draft_round: int | None = None,
        team_id: int | None = None,
        force_update: bool = False,
    ) -> pl.DataFrame:
        """Fetch MLB draft details for a specific season."""
        if year < MLB_FIRST_YEAR or year > most_recent_season() + 1:
            raise InvalidParameterError(f"Invalid draft season: {year}.")
        if draft_round is not None and draft_round <= 0:
            raise InvalidParameterError("draft_round must be a positive integer.")
        if team_id is not None and team_id <= 0:
            raise InvalidParameterError("team_id must be a positive integer.")

        url = draft_url(year)
        df = await self._gateway.fetch(
            url,
            None,
            "Failed to fetch or parse MLB draft data",
            lambda d: parse_mlb_draft(d, year),
            use_cache=True,
            max_age=MLB_CACHE_MAX_AGE,
            force_update=force_update,
        )
        if df.is_empty():
            return df
        if draft_round is not None:
            df = df.filter(pl.col("round").cast(pl.Int64, strict=False) == draft_round)
        if team_id is not None:
            df = df.filter(pl.col("teamId") == team_id)
        return df

    async def transactions(
        self,
        date: date | str | None = None,
        start_date: date | str | None = None,
        end_date: date | str | None = None,
        team_id: int | None = None,
        player_id: int | None = None,
        sport_id: int = MLB_DEFAULT_SPORT_ID,
        force_update: bool = False,
    ) -> pl.DataFrame:
        """Fetch MLB transaction details."""
        filters = TransactionsFilterParams(
            date=coerce_datestring(date),
            start_date=coerce_datestring(start_date),
            end_date=coerce_datestring(end_date),
            team_id=team_id,
            player_id=player_id,
            sport_id=sport_id,
        )
        filters.validate()

        return await self._gateway.fetch(
            transactions_url(),
            filters.to_params(),
            "Failed to fetch or parse MLB transactions data",
            parse_mlb_transactions,
            use_cache=True,
            max_age=MLB_CACHE_MAX_AGE,
            force_update=force_update,
        )

    async def prospect_rankings(
        self,
        list_type: str = "top100",
        year: int | None = None,
        force_update: bool = False,
    ) -> pl.DataFrame:
        """Fetch MLB Pipeline prospect rankings."""
        list_type_clean = list_type.lower().strip()
        if year is not None:
            max_year = most_recent_season() + 4
            if year < PROSPECT_RANKINGS_START_YEAR or year > max_year:
                raise InvalidParameterError(f"Year must be between {PROSPECT_RANKINGS_START_YEAR} and {max_year}.")
            base_path = f"{MILB_ROOT}/prospects/{year}"
        else:
            base_path = f"{MILB_ROOT}/prospects"

        url = base_path if list_type_clean == "top100" else f"{base_path}/{list_type_clean}"

        async def _fetch() -> pl.DataFrame:
            html_str = await self._gateway.fetch_text(url, f"MLB pipeline prospects returned empty response for: {url}")
            return MLBPipelineParser().parse(html_str)

        key = generate_cache_key(
            "milb/prospect_rankings", {"list_type": list_type_clean, "year": "current" if year is None else str(year)}
        )
        return await self._client.cache.get_or_fetch(key, _fetch, max_age=MLB_CACHE_MAX_AGE, force_update=force_update)

    async def _resolve_prospects_url(self, team_name: str | None) -> str:
        if team_name is None:
            return f"{MLB_ROOT}/prospects/stats/top-prospects"
        team_id = await self.resolve_team_id(team_name)
        return f"{MLB_ROOT}/prospects/stats?teamId={team_id}"

    async def top_prospects(
        self,
        team_name: str | None = None,
        player_type: str | None = None,
        force_update: bool = False,
    ) -> pl.DataFrame:
        """Fetch MLB top prospects for a team or the full league."""
        if player_type is not None and player_type not in _VALID_PROSPECT_TYPES:
            raise InvalidParameterError("player_type must be one of: batters, pitchers.")

        async def _fetch() -> pl.DataFrame:
            url = await self._resolve_prospects_url(team_name)
            html_str = await self._gateway.fetch_text(url, "MLB top prospects returned empty response.")
            dfs = MLBApiParser().parse_tables(html_str)
            return _clean_prospect_df(_extract_prospect_df(dfs, player_type))

        clean_team = "league" if team_name is None else team_name.lower().strip()
        clean_type = "all" if player_type is None else player_type.lower().strip()
        key = generate_cache_key("mlb/top_prospects", {"team": clean_team, "type": clean_type})
        return await self._client.cache.get_or_fetch(key, _fetch, max_age=MLB_CACHE_MAX_AGE, force_update=force_update)
