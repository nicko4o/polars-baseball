from __future__ import annotations

import enum
from collections.abc import Sequence
from dataclasses import dataclass, field

import polars as pl

from polars_baseball._config import FG_LEADERS_URL, FG_MAX_RESULTS
from polars_baseball.context import BaseballContext
from polars_baseball.enums.fangraphs import (
    FangraphsLeague,
    FangraphsMonth,
    FangraphsPositions,
    FangraphsStatColumn,
    FangraphsStatsBase,
    FangraphsStatsCategory,
    stat_list_from_str,
    stat_list_to_str,
)
from polars_baseball.exceptions import InvalidParameterError
from polars_baseball.gateways.fangraphs import FanGraphsGateway

OPERATOR_MAP: dict[str, str] = {
    ">": "gt",
    "gt": "gt",
    ">=": "gte",
    "gte": "gte",
    "<": "lt",
    "lt": "lt",
    "<=": "lte",
    "lte": "lte",
    "=": "eq",
    "==": "eq",
    "eq": "eq",
    "!=": "ne",
    "ne": "ne",
}


class FanGraphsFilterOp(enum.StrEnum):
    GT = "gt"
    LT = "lt"
    GTE = "gte"
    LTE = "lte"
    EQ = "eq"
    NE = "ne"


@dataclass(frozen=True)
class FanGraphsFilter:
    column: str
    operator: FanGraphsFilterOp | str
    value: int | float | str

    def __post_init__(self) -> None:
        raw_op = self.operator.value if isinstance(self.operator, FanGraphsFilterOp) else str(self.operator).lower()
        if raw_op not in OPERATOR_MAP:
            valid_ops = ", ".join(
                f"'{k}'" for k in (">", ">=", "<", "<=", "==", "!=", "gt", "gte", "lt", "lte", "eq", "ne")
            )
            raise InvalidParameterError(f"Invalid operator '{self.operator}'. Supported operators: {valid_ops}")
        object.__setattr__(self, "operator", OPERATOR_MAP[raw_op])

    @classmethod
    def gt(cls, column: str, value: int | float | str) -> FanGraphsFilter:
        return cls(column, "gt", value)

    @classmethod
    def gte(cls, column: str, value: int | float | str) -> FanGraphsFilter:
        return cls(column, "gte", value)

    @classmethod
    def lt(cls, column: str, value: int | float | str) -> FanGraphsFilter:
        return cls(column, "lt", value)

    @classmethod
    def lte(cls, column: str, value: int | float | str) -> FanGraphsFilter:
        return cls(column, "lte", value)

    @classmethod
    def eq(cls, column: str, value: int | float | str) -> FanGraphsFilter:
        return cls(column, "eq", value)

    @classmethod
    def ne(cls, column: str, value: int | float | str) -> FanGraphsFilter:
        return cls(column, "ne", value)

    @classmethod
    def coerce(cls, item: FanGraphsFilterInput) -> FanGraphsFilter:
        if isinstance(item, cls):
            return item
        if isinstance(item, tuple) and len(item) == 3:
            return cls(item[0], item[1], item[2])
        raise TypeError(f"Expected FanGraphsFilter or 3-tuple (column, operator, value), got {type(item)}")


FanGraphsFilterInput = FanGraphsFilter | tuple[str, str, int | float | str]


def _validate_enum_field(value: object, enum_type: type, field_name: str) -> None:
    if not isinstance(value, enum_type):
        raise TypeError(f"{field_name} must be a {enum_type.__name__}, got {type(value)}")


def _validate_list_of_enum(value: object, enum_type: type, field_name: str) -> None:
    if not isinstance(value, list) or not all(isinstance(x, enum_type) for x in value):
        raise TypeError(f"{field_name} must be a list of {enum_type.__name__}, got {type(value)}")


def _resolve_stats_category(value: str | FangraphsStatsCategory) -> FangraphsStatsCategory:
    return FangraphsStatsCategory.parse(value.upper()) if isinstance(value, str) else value


def _resolve_league(value: str | FangraphsLeague) -> FangraphsLeague:
    return FangraphsLeague.parse(value.upper()) if isinstance(value, str) else value


def _resolve_month(value: str | FangraphsMonth) -> FangraphsMonth:
    return FangraphsMonth.parse(value.upper()) if isinstance(value, str) else value


def _resolve_position(value: str | FangraphsPositions) -> FangraphsPositions:
    return FangraphsPositions.parse(value.upper()) if isinstance(value, str) else value


def _serialize_filters(filters: Sequence[FanGraphsFilterInput]) -> str:
    parts: list[str] = []
    for f_input in filters:
        f = FanGraphsFilter.coerce(f_input)
        op = f.operator.value if isinstance(f.operator, FanGraphsFilterOp) else f.operator
        parts.append(f"{f.column},{op},{f.value}")
    return "|".join(parts)


@dataclass(frozen=True)
class FanGraphsRequest:
    start_season: int
    end_season: int | None = None
    stats_category: FangraphsStatsCategory = FangraphsStatsCategory.BATTING
    league: FangraphsLeague = FangraphsLeague.ALL
    month: FangraphsMonth = FangraphsMonth.ALL
    position: FangraphsPositions = FangraphsPositions.ALL
    stat_columns: list[FangraphsStatColumn] = field(default_factory=list)
    qual: int | None = None
    split_seasons: bool = True
    ind: int = 1
    on_active_roster: bool = False
    minimum_age: int = 0
    maximum_age: int = 100
    team: str = ""
    filters: list[FanGraphsFilter] = field(default_factory=list)
    players: str = ""
    max_results: int = FG_MAX_RESULTS
    is_team_data: bool = False
    _row_id_name: str = "IDfg"
    _row_id_param: str = "playerid"

    def __post_init__(self) -> None:
        if self.end_season is None:
            object.__setattr__(self, "end_season", self.start_season)

        if isinstance(self.stats_category, str):
            object.__setattr__(self, "stats_category", _resolve_stats_category(self.stats_category))
        if isinstance(self.league, str):
            object.__setattr__(self, "league", _resolve_league(self.league))
        if isinstance(self.month, str):
            object.__setattr__(self, "month", _resolve_month(self.month))
        if isinstance(self.position, str):
            object.__setattr__(self, "position", _resolve_position(self.position))
        if isinstance(self.filters, list):
            coerced_filters = [FanGraphsFilter.coerce(f) for f in self.filters]
            object.__setattr__(self, "filters", coerced_filters)

        _validate_enum_field(self.stats_category, FangraphsStatsCategory, "stats_category")
        _validate_enum_field(self.league, FangraphsLeague, "league")
        _validate_enum_field(self.month, FangraphsMonth, "month")
        _validate_enum_field(self.position, FangraphsPositions, "position")
        _validate_list_of_enum(self.stat_columns, FangraphsStatsBase, "stat_columns")

        if not self.stat_columns:
            object.__setattr__(self, "stat_columns", stat_list_from_str(self.stats_category, "ALL"))

    @classmethod
    def from_raw(
        cls,
        start_season: int,
        *,
        end_season: int | None = None,
        stats_category: str | FangraphsStatsCategory = FangraphsStatsCategory.BATTING,
        league: str | FangraphsLeague = FangraphsLeague.ALL,
        month: str | FangraphsMonth = FangraphsMonth.ALL,
        position: str | FangraphsPositions = FangraphsPositions.ALL,
        stat_columns: str | list[str] | list[FangraphsStatColumn] = "ALL",
        qual: int | None = None,
        split_seasons: bool = True,
        ind: int = 1,
        on_active_roster: bool = False,
        minimum_age: int = 0,
        maximum_age: int = 100,
        team: str = "",
        filters: Sequence[FanGraphsFilterInput] | None = None,
        players: str = "",
        max_results: int = FG_MAX_RESULTS,
        is_team_data: bool = False,
    ) -> FanGraphsRequest:
        """Create a FanGraphsRequest from raw string or enum inputs."""
        resolved_category = _resolve_stats_category(stats_category)
        resolved_columns = stat_list_from_str(resolved_category, stat_columns)

        return cls(
            start_season=start_season,
            end_season=end_season,
            stats_category=resolved_category,
            league=_resolve_league(league),
            month=_resolve_month(month),
            position=_resolve_position(position),
            stat_columns=resolved_columns,
            qual=qual,
            split_seasons=split_seasons,
            ind=ind,
            on_active_roster=on_active_roster,
            minimum_age=minimum_age,
            maximum_age=maximum_age,
            team=team,
            filters=[FanGraphsFilter.coerce(f) for f in filters] if filters else [],
            players=players,
            max_results=max_results,
            is_team_data=is_team_data,
        )

    @classmethod
    def batting(
        cls,
        start_season: int,
        *,
        end_season: int | None = None,
        league: str | FangraphsLeague = FangraphsLeague.ALL,
        month: str | FangraphsMonth = FangraphsMonth.ALL,
        position: str | FangraphsPositions = FangraphsPositions.ALL,
        stat_columns: str | list[str] | list[FangraphsStatColumn] = "ALL",
        qual: int | None = None,
        split_seasons: bool = True,
        ind: int = 1,
        on_active_roster: bool = False,
        minimum_age: int = 0,
        maximum_age: int = 100,
        team: str = "",
        filters: Sequence[FanGraphsFilterInput] | None = None,
        players: str = "",
        max_results: int = FG_MAX_RESULTS,
    ) -> FanGraphsRequest:
        return cls.from_raw(
            start_season=start_season,
            end_season=end_season,
            stats_category=FangraphsStatsCategory.BATTING,
            league=league,
            month=month,
            position=position,
            stat_columns=stat_columns,
            qual=qual,
            split_seasons=split_seasons,
            ind=ind,
            on_active_roster=on_active_roster,
            minimum_age=minimum_age,
            maximum_age=maximum_age,
            team=team,
            filters=filters,
            players=players,
            max_results=max_results,
        )

    @classmethod
    def pitching(
        cls,
        start_season: int,
        *,
        end_season: int | None = None,
        league: str | FangraphsLeague = FangraphsLeague.ALL,
        month: str | FangraphsMonth = FangraphsMonth.ALL,
        position: str | FangraphsPositions = FangraphsPositions.ALL,
        stat_columns: str | list[str] | list[FangraphsStatColumn] = "ALL",
        qual: int | None = None,
        split_seasons: bool = True,
        ind: int = 1,
        on_active_roster: bool = False,
        minimum_age: int = 0,
        maximum_age: int = 100,
        team: str = "",
        filters: Sequence[FanGraphsFilterInput] | None = None,
        players: str = "",
        max_results: int = FG_MAX_RESULTS,
    ) -> FanGraphsRequest:
        return cls.from_raw(
            start_season=start_season,
            end_season=end_season,
            stats_category=FangraphsStatsCategory.PITCHING,
            league=league,
            month=month,
            position=position,
            stat_columns=stat_columns,
            qual=qual,
            split_seasons=split_seasons,
            ind=ind,
            on_active_roster=on_active_roster,
            minimum_age=minimum_age,
            maximum_age=maximum_age,
            team=team,
            filters=filters,
            players=players,
            max_results=max_results,
        )

    @classmethod
    def fielding(
        cls,
        start_season: int,
        *,
        end_season: int | None = None,
        league: str | FangraphsLeague = FangraphsLeague.ALL,
        month: str | FangraphsMonth = FangraphsMonth.ALL,
        position: str | FangraphsPositions = FangraphsPositions.ALL,
        stat_columns: str | list[str] | list[FangraphsStatColumn] = "ALL",
        qual: int | None = None,
        split_seasons: bool = True,
        ind: int = 1,
        on_active_roster: bool = False,
        minimum_age: int = 0,
        maximum_age: int = 100,
        team: str = "",
        filters: Sequence[FanGraphsFilterInput] | None = None,
        players: str = "",
        max_results: int = FG_MAX_RESULTS,
    ) -> FanGraphsRequest:
        return cls.from_raw(
            start_season=start_season,
            end_season=end_season,
            stats_category=FangraphsStatsCategory.FIELDING,
            league=league,
            month=month,
            position=position,
            stat_columns=stat_columns,
            qual=qual,
            split_seasons=split_seasons,
            ind=ind,
            on_active_roster=on_active_roster,
            minimum_age=minimum_age,
            maximum_age=maximum_age,
            team=team,
            filters=filters,
            players=players,
            max_results=max_results,
        )

    @classmethod
    def team_batting(
        cls,
        start_season: int,
        *,
        end_season: int | None = None,
        league: str | FangraphsLeague = FangraphsLeague.ALL,
        month: str | FangraphsMonth = FangraphsMonth.ALL,
        position: str | FangraphsPositions = FangraphsPositions.ALL,
        stat_columns: str | list[str] | list[FangraphsStatColumn] = "ALL",
        qual: int | None = None,
        split_seasons: bool = True,
        ind: int = 1,
        on_active_roster: bool = False,
        minimum_age: int = 0,
        maximum_age: int = 100,
        team: str = "",
        filters: Sequence[FanGraphsFilterInput] | None = None,
        players: str = "",
        max_results: int = FG_MAX_RESULTS,
    ) -> FanGraphsRequest:
        return cls.from_raw(
            start_season=start_season,
            end_season=end_season,
            stats_category=FangraphsStatsCategory.BATTING,
            league=league,
            month=month,
            position=position,
            stat_columns=stat_columns,
            qual=qual,
            split_seasons=split_seasons,
            ind=ind,
            on_active_roster=on_active_roster,
            minimum_age=minimum_age,
            maximum_age=maximum_age,
            team=team,
            filters=filters,
            players=players,
            max_results=max_results,
            is_team_data=True,
        )

    @classmethod
    def team_pitching(
        cls,
        start_season: int,
        *,
        end_season: int | None = None,
        league: str | FangraphsLeague = FangraphsLeague.ALL,
        month: str | FangraphsMonth = FangraphsMonth.ALL,
        position: str | FangraphsPositions = FangraphsPositions.ALL,
        stat_columns: str | list[str] | list[FangraphsStatColumn] = "ALL",
        qual: int | None = None,
        split_seasons: bool = True,
        ind: int = 1,
        on_active_roster: bool = False,
        minimum_age: int = 0,
        maximum_age: int = 100,
        team: str = "",
        filters: Sequence[FanGraphsFilterInput] | None = None,
        players: str = "",
        max_results: int = FG_MAX_RESULTS,
    ) -> FanGraphsRequest:
        return cls.from_raw(
            start_season=start_season,
            end_season=end_season,
            stats_category=FangraphsStatsCategory.PITCHING,
            league=league,
            month=month,
            position=position,
            stat_columns=stat_columns,
            qual=qual,
            split_seasons=split_seasons,
            ind=ind,
            on_active_roster=on_active_roster,
            minimum_age=minimum_age,
            maximum_age=maximum_age,
            team=team,
            filters=filters,
            players=players,
            max_results=max_results,
            is_team_data=True,
        )

    @classmethod
    def team_fielding(
        cls,
        start_season: int,
        *,
        end_season: int | None = None,
        league: str | FangraphsLeague = FangraphsLeague.ALL,
        month: str | FangraphsMonth = FangraphsMonth.ALL,
        position: str | FangraphsPositions = FangraphsPositions.ALL,
        stat_columns: str | list[str] | list[FangraphsStatColumn] = "ALL",
        qual: int | None = None,
        split_seasons: bool = True,
        ind: int = 1,
        on_active_roster: bool = False,
        minimum_age: int = 0,
        maximum_age: int = 100,
        team: str = "",
        filters: Sequence[FanGraphsFilterInput] | None = None,
        players: str = "",
        max_results: int = FG_MAX_RESULTS,
    ) -> FanGraphsRequest:
        return cls.from_raw(
            start_season=start_season,
            end_season=end_season,
            stats_category=FangraphsStatsCategory.FIELDING,
            league=league,
            month=month,
            position=position,
            stat_columns=stat_columns,
            qual=qual,
            split_seasons=split_seasons,
            ind=ind,
            on_active_roster=on_active_roster,
            minimum_age=minimum_age,
            maximum_age=maximum_age,
            team=team,
            filters=filters,
            players=players,
            max_results=max_results,
            is_team_data=True,
        )

    @classmethod
    def team_starters(
        cls,
        start_season: int,
        *,
        end_season: int | None = None,
        league: str | FangraphsLeague = FangraphsLeague.ALL,
        month: str | FangraphsMonth = FangraphsMonth.ALL,
        position: str | FangraphsPositions = FangraphsPositions.ALL,
        stat_columns: str | list[str] | list[FangraphsStatColumn] = "ALL",
        qual: int | None = None,
        split_seasons: bool = True,
        ind: int = 1,
        on_active_roster: bool = False,
        minimum_age: int = 0,
        maximum_age: int = 100,
        team: str = "",
        filters: Sequence[FanGraphsFilterInput] | None = None,
        players: str = "",
        max_results: int = FG_MAX_RESULTS,
    ) -> FanGraphsRequest:
        return cls.from_raw(
            start_season=start_season,
            end_season=end_season,
            stats_category=FangraphsStatsCategory.STARTERS,
            league=league,
            month=month,
            position=position,
            stat_columns=stat_columns,
            qual=qual,
            split_seasons=split_seasons,
            ind=ind,
            on_active_roster=on_active_roster,
            minimum_age=minimum_age,
            maximum_age=maximum_age,
            team=team,
            filters=filters,
            players=players,
            max_results=max_results,
            is_team_data=True,
        )

    @classmethod
    def team_relievers(
        cls,
        start_season: int,
        *,
        end_season: int | None = None,
        league: str | FangraphsLeague = FangraphsLeague.ALL,
        month: str | FangraphsMonth = FangraphsMonth.ALL,
        position: str | FangraphsPositions = FangraphsPositions.ALL,
        stat_columns: str | list[str] | list[FangraphsStatColumn] = "ALL",
        qual: int | None = None,
        split_seasons: bool = True,
        ind: int = 1,
        on_active_roster: bool = False,
        minimum_age: int = 0,
        maximum_age: int = 100,
        team: str = "",
        filters: list[FanGraphsFilter] | None = None,
        players: str = "",
        max_results: int = FG_MAX_RESULTS,
    ) -> FanGraphsRequest:
        return cls.from_raw(
            start_season=start_season,
            end_season=end_season,
            stats_category=FangraphsStatsCategory.RELIEVERS,
            league=league,
            month=month,
            position=position,
            stat_columns=stat_columns,
            qual=qual,
            split_seasons=split_seasons,
            ind=ind,
            on_active_roster=on_active_roster,
            minimum_age=minimum_age,
            maximum_age=maximum_age,
            team=team,
            filters=filters,
            players=players,
            max_results=max_results,
            is_team_data=True,
        )


def _build_fg_url_options(request: FanGraphsRequest) -> dict[str, object]:
    page_params = {"pageitems": str(request.max_results), "pagenum": "1"}
    team = f"{request.team or 0},ts" if request.is_team_data else request.team
    ind = request.ind if request.ind == 0 else int(request.split_seasons)
    position: FangraphsPositions = request.position
    league: FangraphsLeague = request.league
    month: FangraphsMonth = request.month
    return {
        "pos": position.value,
        "stats": request.stats_category.value,
        "lg": league.value,
        "qual": request.qual if request.qual is not None else "y",
        "type": stat_list_to_str(request.stat_columns),
        "season": request.end_season,
        "month": month.value,
        "season1": request.start_season,
        "ind": ind,
        "team": team,
        "rost": int(request.on_active_roster),
        "age": f"{request.minimum_age},{request.maximum_age}",
        "filter": _serialize_filters(request.filters),
        "players": request.players,
        **page_params,
    }


async def fg_data(request: FanGraphsRequest, context: BaseballContext | None = None) -> pl.DataFrame:
    """Execute a pre-built FanGraphs request and return the parsed results.

    Uses ``curl_cffi`` (via :class:`BaseballContext`) to bypass Cloudflare protection.
    Results are transparently cached behind the ``@cached`` decorator.

    Note:
        - Returns empty DataFrame when the upstream HTML contains no data table.
        - FanGraphs rate-limiting or Cloudflare challenges may cause delays or failures.
    """
    ctx = context or BaseballContext.default()
    return await FanGraphsGateway(ctx).get_leaderboard(FG_LEADERS_URL, _build_fg_url_options(request))
