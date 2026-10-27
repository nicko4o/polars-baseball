"""Namespaced client for FanGraphs leaderboards and statistics."""

from __future__ import annotations

import enum
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import timedelta
from typing import TYPE_CHECKING

import polars as pl

from polars_baseball._config import (
    FG_ACTIVE_SEASON_CACHE_TTL,
    FG_LEADERS_URL,
    FG_MAX_RESULTS,
)
from polars_baseball._season import most_recent_season
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

if TYPE_CHECKING:
    from polars_baseball.client import BaseballClient

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


FG_MIN_SCHEDULE_SEASON = 2002

_FG_TEAM_SLUGS: dict[int, tuple[str, ...]] = {
    1: ("angels", "anaheim-angels", "los-angeles-angels"),
    2: ("orioles", "baltimore-orioles"),
    3: ("red-sox", "boston-red-sox"),
    4: ("white-sox", "chicago-white-sox"),
    5: ("guardians", "indians", "cleveland-guardians", "cleveland-indians"),
    6: ("tigers", "detroit-tigers"),
    7: ("royals", "kansas-city-royals"),
    8: ("twins", "minnesota-twins"),
    9: ("yankees", "new-york-yankees"),
    10: ("athletics", "oakland-athletics", "as"),
    11: ("mariners", "seattle-mariners"),
    12: ("rays", "tampa-bay-rays", "devil-rays"),
    13: ("rangers", "texas-rangers"),
    14: ("blue-jays", "toronto-blue-jays"),
    15: ("diamondbacks", "dbacks", "arizona-diamondbacks"),
    16: ("braves", "atlanta-braves"),
    17: ("cubs", "chicago-cubs"),
    18: ("reds", "cincinnati-reds"),
    19: ("rockies", "colorado-rockies"),
    20: ("marlins", "miami-marlins", "florida-marlins"),
    21: ("astros", "houston-astros"),
    22: ("dodgers", "los-angeles-dodgers"),
    23: ("brewers", "milwaukee-brewers"),
    24: ("nationals", "washington-nationals", "expos"),
    25: ("mets", "new-york-mets"),
    26: ("phillies", "philadelphia-phillies"),
    27: ("pirates", "pittsburgh-pirates"),
    28: ("cardinals", "st-louis-cardinals"),
    29: ("padres", "san-diego-padres"),
    30: ("giants", "san-francisco-giants"),
}

_FG_TEAM_ABBRS: dict[str, int] = {
    "ANA": 1,
    "ARI": 15,
    "ATL": 16,
    "BAL": 2,
    "BOS": 3,
    "CAL": 1,
    "CHA": 4,
    "CHC": 17,
    "CHN": 17,
    "CHW": 4,
    "CIN": 18,
    "CLE": 5,
    "COL": 19,
    "DET": 6,
    "FLA": 20,
    "FLO": 20,
    "HOU": 21,
    "KCA": 7,
    "KCR": 7,
    "LAA": 1,
    "LAD": 22,
    "LAN": 22,
    "MIA": 20,
    "MIL": 23,
    "MIN": 8,
    "ML4": 23,
    "MON": 24,
    "NYA": 9,
    "NYM": 25,
    "NYN": 25,
    "NYY": 9,
    "OAK": 10,
    "PHI": 26,
    "PIT": 27,
    "SDN": 29,
    "SDP": 29,
    "SEA": 11,
    "SFG": 30,
    "SFN": 30,
    "SLN": 28,
    "STL": 28,
    "TBA": 12,
    "TBD": 12,
    "TBR": 12,
    "TEX": 13,
    "TOR": 14,
    "WAS": 24,
    "WS2": 13,
    "WSA": 13,
    "WSN": 24,
}


def _build_team_lookup() -> dict[str, int]:
    lookup: dict[str, int] = {}
    for abbr, tid in _FG_TEAM_ABBRS.items():
        lookup[abbr.lower()] = tid
    for tid, slugs in _FG_TEAM_SLUGS.items():
        for slug in slugs:
            lookup[slug] = tid
            lookup[slug.replace("-", "")] = tid
            lookup[slug.replace("-", " ")] = tid
    return lookup


_FG_TEAM_LOOKUP: dict[str, int] = _build_team_lookup()


def resolve_fangraphs_team_id(team: str | int) -> int:
    """Resolve team name, slug, abbreviation, or numeric id to FanGraphs team ID."""
    if isinstance(team, int):
        if 1 <= team <= 30:
            return team
        raise InvalidParameterError(f"Invalid FanGraphs team id '{team}'. Expected integer between 1 and 30.")

    clean = str(team).strip().lower().replace("_", "-").replace(".", "")
    if clean.isdigit():
        return resolve_fangraphs_team_id(int(clean))

    if clean in _FG_TEAM_LOOKUP:
        return _FG_TEAM_LOOKUP[clean]

    clean_space = clean.replace("-", " ")
    if clean_space in _FG_TEAM_LOOKUP:
        return _FG_TEAM_LOOKUP[clean_space]

    clean_nospace = clean.replace("-", "")
    if clean_nospace in _FG_TEAM_LOOKUP:
        return _FG_TEAM_LOOKUP[clean_nospace]

    raise InvalidParameterError(
        f"Unknown team identifier '{team}'. Provide a valid team slug (e.g. 'yankees'), "
        f"abbreviation (e.g. 'NYY'), or FanGraphs team id (e.g. 9)."
    )


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


@dataclass(frozen=True)
class FanGraphsLeaderboardParams:
    start_season: int
    end_season: int | None = None
    league: str | FangraphsLeague = FangraphsLeague.ALL
    month: str | FangraphsMonth = FangraphsMonth.ALL
    position: str | FangraphsPositions = FangraphsPositions.ALL
    stat_columns: str | list[str] | list[FangraphsStatColumn] = "ALL"
    qual: int | None = None
    split_seasons: bool = True
    on_active_roster: bool = False
    minimum_age: int = 0
    maximum_age: int = 100
    team: str = ""
    filters: Sequence[FanGraphsFilterInput] | None = None
    players: str = ""
    max_results: int = FG_MAX_RESULTS
    ind: int = 1


class FanGraphsClient:
    """Namespaced FanGraphs client."""

    def __init__(self, client: BaseballClient) -> None:
        self._client = client
        self._gateway = FanGraphsGateway(client)

    async def _execute_fg_query(
        self,
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
        force_update: bool = False,
        cache_max_age: timedelta | None = None,
    ) -> pl.DataFrame:
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

        effective_max_age = _resolve_fg_cache_max_age(resolved_end_season, cache_max_age)
        df = await self._gateway.get_leaderboard(
            FG_LEADERS_URL,
            options,
            max_age=effective_max_age,
            force_update=force_update,
        )
        return _apply_filters(df, coerced_filters)

    async def _dispatch_fg(
        self,
        category: FangraphsStatsCategory,
        is_team_data: bool,
        params: FanGraphsLeaderboardParams,
        force_update: bool,
        cache_max_age: timedelta | None,
    ) -> pl.DataFrame:
        return await self._execute_fg_query(
            params.start_season,
            end_season=params.end_season,
            stats_category=category,
            league=params.league,
            month=params.month,
            position=params.position,
            stat_columns=params.stat_columns,
            qual=params.qual,
            split_seasons=params.split_seasons,
            ind=params.ind,
            on_active_roster=params.on_active_roster,
            minimum_age=params.minimum_age,
            maximum_age=params.maximum_age,
            team=params.team,
            filters=params.filters,
            players=params.players,
            max_results=params.max_results,
            is_team_data=is_team_data,
            force_update=force_update,
            cache_max_age=cache_max_age,
        )

    async def fg_data(
        self,
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
        force_update: bool = False,
        cache_max_age: timedelta | None = None,
    ) -> pl.DataFrame:
        """Fetch and return parsed FanGraphs leaderboard results."""
        return await self._execute_fg_query(
            start_season,
            end_season=end_season,
            stats_category=stats_category,
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
            is_team_data=is_team_data,
            force_update=force_update,
            cache_max_age=cache_max_age,
        )

    async def batting(
        self,
        start_season: int,
        *,
        end_season: int | None = None,
        league: str | FangraphsLeague = FangraphsLeague.ALL,
        month: str | FangraphsMonth = FangraphsMonth.ALL,
        position: str | FangraphsPositions = FangraphsPositions.ALL,
        stat_columns: str | list[str] | list[FangraphsStatColumn] = "ALL",
        qual: int | None = None,
        split_seasons: bool = True,
        on_active_roster: bool = False,
        minimum_age: int = 0,
        maximum_age: int = 100,
        filters: Sequence[FanGraphsFilterInput] | None = None,
        players: str = "",
        max_results: int = FG_MAX_RESULTS,
        force_update: bool = False,
        cache_max_age: timedelta | None = None,
    ) -> pl.DataFrame:
        """Fetch FanGraphs player batting leaderboards."""
        params = FanGraphsLeaderboardParams(
            start_season=start_season,
            end_season=end_season,
            league=league,
            month=month,
            position=position,
            stat_columns=stat_columns,
            qual=qual,
            split_seasons=split_seasons,
            on_active_roster=on_active_roster,
            minimum_age=minimum_age,
            maximum_age=maximum_age,
            filters=filters,
            players=players,
            max_results=max_results,
        )
        return await self._dispatch_fg(FangraphsStatsCategory.BATTING, False, params, force_update, cache_max_age)

    async def pitching(
        self,
        start_season: int,
        *,
        end_season: int | None = None,
        league: str | FangraphsLeague = FangraphsLeague.ALL,
        month: str | FangraphsMonth = FangraphsMonth.ALL,
        position: str | FangraphsPositions = FangraphsPositions.ALL,
        stat_columns: str | list[str] | list[FangraphsStatColumn] = "ALL",
        qual: int | None = None,
        split_seasons: bool = True,
        on_active_roster: bool = False,
        minimum_age: int = 0,
        maximum_age: int = 100,
        filters: Sequence[FanGraphsFilterInput] | None = None,
        players: str = "",
        max_results: int = FG_MAX_RESULTS,
        force_update: bool = False,
        cache_max_age: timedelta | None = None,
    ) -> pl.DataFrame:
        """Fetch FanGraphs player pitching leaderboards."""
        params = FanGraphsLeaderboardParams(
            start_season=start_season,
            end_season=end_season,
            league=league,
            month=month,
            position=position,
            stat_columns=stat_columns,
            qual=qual,
            split_seasons=split_seasons,
            on_active_roster=on_active_roster,
            minimum_age=minimum_age,
            maximum_age=maximum_age,
            filters=filters,
            players=players,
            max_results=max_results,
        )
        return await self._dispatch_fg(FangraphsStatsCategory.PITCHING, False, params, force_update, cache_max_age)

    async def fielding(
        self,
        start_season: int,
        *,
        end_season: int | None = None,
        league: str | FangraphsLeague = FangraphsLeague.ALL,
        month: str | FangraphsMonth = FangraphsMonth.ALL,
        position: str | FangraphsPositions = FangraphsPositions.ALL,
        stat_columns: str | list[str] | list[FangraphsStatColumn] = "ALL",
        qual: int | None = None,
        split_seasons: bool = True,
        on_active_roster: bool = False,
        minimum_age: int = 0,
        maximum_age: int = 100,
        filters: Sequence[FanGraphsFilterInput] | None = None,
        players: str = "",
        max_results: int = FG_MAX_RESULTS,
        force_update: bool = False,
        cache_max_age: timedelta | None = None,
    ) -> pl.DataFrame:
        """Fetch FanGraphs player fielding leaderboards."""
        params = FanGraphsLeaderboardParams(
            start_season=start_season,
            end_season=end_season,
            league=league,
            month=month,
            position=position,
            stat_columns=stat_columns,
            qual=qual,
            split_seasons=split_seasons,
            on_active_roster=on_active_roster,
            minimum_age=minimum_age,
            maximum_age=maximum_age,
            filters=filters,
            players=players,
            max_results=max_results,
        )
        return await self._dispatch_fg(FangraphsStatsCategory.FIELDING, False, params, force_update, cache_max_age)

    async def team_batting(
        self,
        start_season: int,
        *,
        end_season: int | None = None,
        league: str | FangraphsLeague = FangraphsLeague.ALL,
        month: str | FangraphsMonth = FangraphsMonth.ALL,
        position: str | FangraphsPositions = FangraphsPositions.ALL,
        stat_columns: str | list[str] | list[FangraphsStatColumn] = "ALL",
        qual: int | None = None,
        split_seasons: bool = True,
        on_active_roster: bool = False,
        minimum_age: int = 0,
        maximum_age: int = 100,
        team: str = "",
        filters: Sequence[FanGraphsFilterInput] | None = None,
        players: str = "",
        max_results: int = FG_MAX_RESULTS,
        force_update: bool = False,
        cache_max_age: timedelta | None = None,
    ) -> pl.DataFrame:
        """Fetch FanGraphs team batting leaderboards."""
        params = FanGraphsLeaderboardParams(
            start_season=start_season,
            end_season=end_season,
            league=league,
            month=month,
            position=position,
            stat_columns=stat_columns,
            qual=qual,
            split_seasons=split_seasons,
            on_active_roster=on_active_roster,
            minimum_age=minimum_age,
            maximum_age=maximum_age,
            team=team,
            filters=filters,
            players=players,
            max_results=max_results,
        )
        return await self._dispatch_fg(FangraphsStatsCategory.BATTING, True, params, force_update, cache_max_age)

    async def team_pitching(
        self,
        start_season: int,
        *,
        end_season: int | None = None,
        league: str | FangraphsLeague = FangraphsLeague.ALL,
        month: str | FangraphsMonth = FangraphsMonth.ALL,
        position: str | FangraphsPositions = FangraphsPositions.ALL,
        stat_columns: str | list[str] | list[FangraphsStatColumn] = "ALL",
        qual: int | None = None,
        split_seasons: bool = True,
        on_active_roster: bool = False,
        minimum_age: int = 0,
        maximum_age: int = 100,
        team: str = "",
        filters: Sequence[FanGraphsFilterInput] | None = None,
        players: str = "",
        max_results: int = FG_MAX_RESULTS,
        force_update: bool = False,
        cache_max_age: timedelta | None = None,
    ) -> pl.DataFrame:
        """Fetch FanGraphs team pitching leaderboards."""
        params = FanGraphsLeaderboardParams(
            start_season=start_season,
            end_season=end_season,
            league=league,
            month=month,
            position=position,
            stat_columns=stat_columns,
            qual=qual,
            split_seasons=split_seasons,
            on_active_roster=on_active_roster,
            minimum_age=minimum_age,
            maximum_age=maximum_age,
            team=team,
            filters=filters,
            players=players,
            max_results=max_results,
        )
        return await self._dispatch_fg(FangraphsStatsCategory.PITCHING, True, params, force_update, cache_max_age)

    async def team_fielding(
        self,
        start_season: int,
        *,
        end_season: int | None = None,
        league: str | FangraphsLeague = FangraphsLeague.ALL,
        month: str | FangraphsMonth = FangraphsMonth.ALL,
        position: str | FangraphsPositions = FangraphsPositions.ALL,
        stat_columns: str | list[str] | list[FangraphsStatColumn] = "ALL",
        qual: int | None = None,
        split_seasons: bool = True,
        on_active_roster: bool = False,
        minimum_age: int = 0,
        maximum_age: int = 100,
        team: str = "",
        filters: Sequence[FanGraphsFilterInput] | None = None,
        players: str = "",
        max_results: int = FG_MAX_RESULTS,
        force_update: bool = False,
        cache_max_age: timedelta | None = None,
    ) -> pl.DataFrame:
        """Fetch FanGraphs team fielding leaderboards."""
        params = FanGraphsLeaderboardParams(
            start_season=start_season,
            end_season=end_season,
            league=league,
            month=month,
            position=position,
            stat_columns=stat_columns,
            qual=qual,
            split_seasons=split_seasons,
            on_active_roster=on_active_roster,
            minimum_age=minimum_age,
            maximum_age=maximum_age,
            team=team,
            filters=filters,
            players=players,
            max_results=max_results,
        )
        return await self._dispatch_fg(FangraphsStatsCategory.FIELDING, True, params, force_update, cache_max_age)

    async def team_starters(
        self,
        start_season: int,
        *,
        end_season: int | None = None,
        league: str | FangraphsLeague = FangraphsLeague.ALL,
        month: str | FangraphsMonth = FangraphsMonth.ALL,
        position: str | FangraphsPositions = FangraphsPositions.ALL,
        stat_columns: str | list[str] | list[FangraphsStatColumn] = "ALL",
        qual: int | None = None,
        split_seasons: bool = True,
        on_active_roster: bool = False,
        minimum_age: int = 0,
        maximum_age: int = 100,
        team: str = "",
        filters: Sequence[FanGraphsFilterInput] | None = None,
        players: str = "",
        max_results: int = FG_MAX_RESULTS,
        force_update: bool = False,
        cache_max_age: timedelta | None = None,
    ) -> pl.DataFrame:
        """Fetch FanGraphs team starting pitcher leaderboards."""
        params = FanGraphsLeaderboardParams(
            start_season=start_season,
            end_season=end_season,
            league=league,
            month=month,
            position=position,
            stat_columns=stat_columns,
            qual=qual,
            split_seasons=split_seasons,
            on_active_roster=on_active_roster,
            minimum_age=minimum_age,
            maximum_age=maximum_age,
            team=team,
            filters=filters,
            players=players,
            max_results=max_results,
        )
        return await self._dispatch_fg(FangraphsStatsCategory.STARTERS, True, params, force_update, cache_max_age)

    async def team_relievers(
        self,
        start_season: int,
        *,
        end_season: int | None = None,
        league: str | FangraphsLeague = FangraphsLeague.ALL,
        month: str | FangraphsMonth = FangraphsMonth.ALL,
        position: str | FangraphsPositions = FangraphsPositions.ALL,
        stat_columns: str | list[str] | list[FangraphsStatColumn] = "ALL",
        qual: int | None = None,
        split_seasons: bool = True,
        on_active_roster: bool = False,
        minimum_age: int = 0,
        maximum_age: int = 100,
        team: str = "",
        filters: Sequence[FanGraphsFilterInput] | None = None,
        players: str = "",
        max_results: int = FG_MAX_RESULTS,
        force_update: bool = False,
        cache_max_age: timedelta | None = None,
    ) -> pl.DataFrame:
        """Fetch FanGraphs team reliever leaderboards."""
        params = FanGraphsLeaderboardParams(
            start_season=start_season,
            end_season=end_season,
            league=league,
            month=month,
            position=position,
            stat_columns=stat_columns,
            qual=qual,
            split_seasons=split_seasons,
            on_active_roster=on_active_roster,
            minimum_age=minimum_age,
            maximum_age=maximum_age,
            team=team,
            filters=filters,
            players=players,
            max_results=max_results,
        )
        return await self._dispatch_fg(FangraphsStatsCategory.RELIEVERS, True, params, force_update, cache_max_age)

    async def season_schedule(
        self,
        team: str | int,
        season: int | None = None,
        *,
        force_update: bool = False,
        cache_max_age: timedelta | None = None,
    ) -> pl.DataFrame:
        """Fetch game-by-game season schedule and results for a team from FanGraphs.

        Args:
            team: Team identifier as a name/slug (e.g. 'yankees', 'red-sox'),
                abbreviation (e.g. 'NYY', 'BOS'), or integer FanGraphs team id (1-30).
            season: Target season year (>= 2002). If None, defaults to the most recent season.
            force_update: If True, bypass cached responses and fetch fresh data.
            cache_max_age: Optional explicit cache lifetime. Defaults to 24h for active season.

        Returns:
            A Polars DataFrame containing game dates, opponents, final scores,
            and home/team win probabilities.
        """
        team_id = resolve_fangraphs_team_id(team)
        target_season = season if season is not None else most_recent_season()
        if target_season < FG_MIN_SCHEDULE_SEASON:
            raise InvalidParameterError(
                f"FanGraphs schedule is not available for season {target_season}. "
                f"Minimum available season is {FG_MIN_SCHEDULE_SEASON}."
            )

        effective_max_age = _resolve_fg_cache_max_age(target_season, cache_max_age)
        return await self._gateway.get_season_schedule(
            target_season,
            team_id,
            max_age=effective_max_age,
            force_update=force_update,
        )


__all__ = [
    "FG_MIN_SCHEDULE_SEASON",
    "FanGraphsClient",
    "FanGraphsFilter",
    "FanGraphsFilterInput",
    "FanGraphsFilterOp",
    "resolve_fangraphs_team_id",
]
