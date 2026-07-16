from __future__ import annotations

from dataclasses import dataclass, field
from typing import TypedDict

import polars as pl
from typing_extensions import Unpack

from polars_baseball._cache import cached, generate_cache_key
from polars_baseball._config import FG_LEADERS_URL, FG_MAX_RESULTS
from polars_baseball.context import BaseballContext, default_context
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
from polars_baseball.parsers.fangraphs import FangraphsHTMLParser


class _FanGraphsKwargs(TypedDict, total=False):
    """Keyword arguments accepted by FanGraphsRequest factory methods.

    Fields accepting ``str | EnumType`` are resolved by ``from_raw()`` before
    being passed to the dataclass constructor.  Do **not** pass raw strings
    directly to ``FanGraphsRequest(...)``; use the factory classmethods
    (``batting``, ``pitching``, ``from_raw``, etc.) which handle parsing.
    """

    start_season: int
    end_season: int | None
    league: str | FangraphsLeague
    month: str | FangraphsMonth
    position: str | FangraphsPositions
    stat_columns: str | list[str] | list[FangraphsStatColumn]
    qual: int | None
    split_seasons: bool
    ind: int
    on_active_roster: bool
    minimum_age: int
    maximum_age: int
    team: str
    _filter: str
    players: str
    max_results: int


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
    _filter: str = ""
    players: str = ""
    max_results: int = FG_MAX_RESULTS
    is_team_data: bool = False
    _row_id_name: str = "IDfg"
    _row_id_param: str = "playerid"

    def __post_init__(self) -> None:
        if self.end_season is None:
            object.__setattr__(self, "end_season", self.start_season)

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
        _filter: str = "",
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
            _filter=_filter,
            players=players,
            max_results=max_results,
            is_team_data=is_team_data,
        )

    @classmethod
    def batting(cls, **kwargs: Unpack[_FanGraphsKwargs]) -> FanGraphsRequest:
        return cls.from_raw(stats_category=FangraphsStatsCategory.BATTING, **kwargs)

    @classmethod
    def pitching(cls, **kwargs: Unpack[_FanGraphsKwargs]) -> FanGraphsRequest:
        return cls.from_raw(stats_category=FangraphsStatsCategory.PITCHING, **kwargs)

    @classmethod
    def fielding(cls, **kwargs: Unpack[_FanGraphsKwargs]) -> FanGraphsRequest:
        return cls.from_raw(stats_category=FangraphsStatsCategory.FIELDING, **kwargs)

    @classmethod
    def team_batting(cls, **kwargs: Unpack[_FanGraphsKwargs]) -> FanGraphsRequest:
        return cls.from_raw(stats_category=FangraphsStatsCategory.BATTING, is_team_data=True, **kwargs)

    @classmethod
    def team_pitching(cls, **kwargs: Unpack[_FanGraphsKwargs]) -> FanGraphsRequest:
        return cls.from_raw(stats_category=FangraphsStatsCategory.PITCHING, is_team_data=True, **kwargs)

    @classmethod
    def team_fielding(cls, **kwargs: Unpack[_FanGraphsKwargs]) -> FanGraphsRequest:
        return cls.from_raw(stats_category=FangraphsStatsCategory.FIELDING, is_team_data=True, **kwargs)

    @classmethod
    def team_starters(cls, **kwargs: Unpack[_FanGraphsKwargs]) -> FanGraphsRequest:
        return cls.from_raw(stats_category=FangraphsStatsCategory.STARTERS, is_team_data=True, **kwargs)

    @classmethod
    def team_relievers(cls, **kwargs: Unpack[_FanGraphsKwargs]) -> FanGraphsRequest:
        return cls.from_raw(stats_category=FangraphsStatsCategory.RELIEVERS, is_team_data=True, **kwargs)


_fg_parser = FangraphsHTMLParser()


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
        "filter": request._filter,
        "players": request.players,
        **page_params,
    }


def _fg_cache_key(request: FanGraphsRequest, _ctx: BaseballContext) -> str:
    return generate_cache_key(FG_LEADERS_URL, _build_fg_url_options(request))


@cached(key=_fg_cache_key)
async def _fetch_fangraphs(request: FanGraphsRequest, ctx: BaseballContext) -> pl.DataFrame:
    url_options = _build_fg_url_options(request)
    html = await ctx.http.get_text(FG_LEADERS_URL, params=url_options)
    return _fg_parser.parse(html)


async def fg_data(request: FanGraphsRequest, context: BaseballContext | None = None) -> pl.DataFrame:
    """Execute a pre-built FanGraphs request and return the parsed results.

    Uses ``curl_cffi`` (via :class:`BaseballContext`) to bypass Cloudflare protection.
    Results are transparently cached behind the ``@cached`` decorator.

    Edge Cases:
        - Returns empty DataFrame when the upstream HTML contains no data table.
        - FanGraphs rate-limiting or Cloudflare challenges may cause delays or failures.
    """
    ctx = context or default_context()
    return await _fetch_fangraphs(request, ctx)
