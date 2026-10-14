from __future__ import annotations

import enum
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import timedelta

import polars as pl

from polars_baseball._config import FG_ACTIVE_SEASON_CACHE_TTL, FG_LEADERS_URL, FG_MAX_RESULTS
from polars_baseball._season import most_recent_season
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
        parts.append(f"{f.column},{f.operator},{f.value}")
    return "|".join(parts)


def _coerce_filter_value(val: int | float | str, dtype: pl.DataType) -> int | float | str:
    if not (isinstance(val, str) and dtype.is_numeric()):
        return val
    try:
        val_float = float(val)
        return int(val_float) if val_float.is_integer() and dtype.is_integer() else val_float
    except ValueError:
        return val


def _apply_filter_op(col_name: str, op: str, val: int | float | str) -> pl.Expr:
    col_expr = pl.col(col_name)
    match op:
        case "gt":
            return col_expr > val
        case "gte":
            return col_expr >= val
        case "lt":
            return col_expr < val
        case "lte":
            return col_expr <= val
        case "eq":
            return col_expr == val
        case "ne":
            return col_expr != val
        case _:
            raise InvalidParameterError(f"Unsupported filter operator '{op}'.")


def _apply_filters(df: pl.DataFrame, filters: Sequence[FanGraphsFilter]) -> pl.DataFrame:
    if df.is_empty() or not filters:
        return df

    exprs: list[pl.Expr] = []
    for f in filters:
        if f.column not in df.columns:
            raise InvalidParameterError(f"Filter column '{f.column}' not found in data columns.")
        val = _coerce_filter_value(f.value, df[f.column].dtype)
        exprs.append(_apply_filter_op(f.column, f.operator, val))

    return df.filter(*exprs)


def _build_fg_url_options(
    start_season: int,
    end_season: int,
    category: FangraphsStatsCategory,
    league: FangraphsLeague,
    month: FangraphsMonth,
    position: FangraphsPositions,
    stat_columns: list[FangraphsStatColumn],
    qual: int | None,
    split_seasons: bool,
    ind: int,
    on_active_roster: bool,
    minimum_age: int,
    maximum_age: int,
    team: str,
    filters: Sequence[FanGraphsFilterInput],
    players: str,
    max_results: int,
    is_team_data: bool,
) -> dict[str, object]:
    page_params = {"pageitems": str(max_results), "pagenum": "1"}
    team_param = f"{team or 0},ts" if is_team_data else team
    ind_val = ind if ind == 0 else int(split_seasons)
    return {
        "pos": position.value,
        "stats": category.value,
        "lg": league.value,
        "qual": qual if qual is not None else "y",
        "type": stat_list_to_str(stat_columns),
        "season": end_season,
        "month": month.value,
        "season1": start_season,
        "ind": ind_val,
        "team": team_param,
        "rost": int(on_active_roster),
        "age": f"{minimum_age},{maximum_age}",
        "filter": _serialize_filters(filters),
        "players": players,
        **page_params,
    }


def _resolve_fg_cache_max_age(end_season: int, cache_max_age: timedelta | None) -> timedelta | None:
    if cache_max_age is not None:
        return cache_max_age
    if end_season >= most_recent_season():
        return FG_ACTIVE_SEASON_CACHE_TTL
    return None


async def fg_data(
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
    context: BaseballContext | None = None,
    force_update: bool = False,
    cache_max_age: timedelta | None = None,
) -> pl.DataFrame:
    """Fetch and return parsed FanGraphs leaderboard results.

    Uses ``curl_cffi`` (via :class:`BaseballContext`) to bypass Cloudflare protection.
    Results are cached in the context cache backend.
    """
    resolved_end_season = start_season if end_season is None else end_season
    resolved_category = _resolve_stats_category(stats_category)
    resolved_league = _resolve_league(league)
    resolved_month = _resolve_month(month)
    resolved_position = _resolve_position(position)
    resolved_columns = stat_list_from_str(resolved_category, stat_columns)

    _validate_enum_field(resolved_category, FangraphsStatsCategory, "stats_category")
    _validate_enum_field(resolved_league, FangraphsLeague, "league")
    _validate_enum_field(resolved_month, FangraphsMonth, "month")
    _validate_enum_field(resolved_position, FangraphsPositions, "position")
    _validate_list_of_enum(resolved_columns, FangraphsStatsBase, "stat_columns")

    coerced_filters = [FanGraphsFilter.coerce(f) for f in filters] if filters else []

    options = _build_fg_url_options(
        start_season=start_season,
        end_season=resolved_end_season,
        category=resolved_category,
        league=resolved_league,
        month=resolved_month,
        position=resolved_position,
        stat_columns=resolved_columns,
        qual=qual,
        split_seasons=split_seasons,
        ind=ind,
        on_active_roster=on_active_roster,
        minimum_age=minimum_age,
        maximum_age=maximum_age,
        team=team,
        filters=coerced_filters,
        players=players,
        max_results=max_results,
        is_team_data=is_team_data,
    )

    ctx = context or BaseballContext.default()
    effective_max_age = _resolve_fg_cache_max_age(resolved_end_season, cache_max_age)
    df = await FanGraphsGateway(ctx).get_leaderboard(
        FG_LEADERS_URL,
        options,
        max_age=effective_max_age,
        force_update=force_update,
    )
    return _apply_filters(df, coerced_filters)
