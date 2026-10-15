"""Namespaced client for MLB Stats API endpoints."""

from __future__ import annotations

import logging
import re
from collections.abc import Sequence
from datetime import date, datetime, timedelta
from typing import TYPE_CHECKING, cast

import polars as pl

from polars_baseball._cache import generate_cache_key
from polars_baseball._config import (
    FILM_ROOM_GRAPHQL_URL,
    MILB_ROOT,
    MLB_FIRST_YEAR,
    MLB_ROOT,
    PROSPECT_RANKINGS_START_YEAR,
    STATS_API_ROOT,
)
from polars_baseball._mlb_contracts import (
    MLB_ACTIVE_ROSTER_TYPE,
    MLB_CACHE_MAX_AGE,
    MLB_DEFAULT_SPORT_ID,
    MLB_DEFAULT_STATS_GROUP,
    MLB_DEFAULT_STATS_TYPE,
    MLB_LIVE_ENDPOINT_CACHE_MAX_AGE,
    MLB_PITCH_ARSENAL_STATS,
    MLB_POSTSEASON_GAME_TYPE,
    boxscore_cache_key,
    boxscore_stats_cache_key,
    boxscore_url,
    divisions_cache_key,
    divisions_url,
    draft_cache_key,
    draft_url,
    game_content_url,
    game_highlights_cache_key,
    leagues_cache_key,
    leagues_url,
    linescore_cache_key,
    linescore_url,
    live_feed_cache_key,
    live_feed_url,
    people_awards_cache_key,
    people_awards_url,
    people_cache_key,
    people_stats_url,
    people_url,
    pitch_arsenal_cache_key,
    play_by_play_cache_key,
    play_by_play_url,
    player_stats_cache_key,
    postseason_cache_key,
    roster_cache_key,
    roster_url,
    schedule_cache_key,
    schedule_url,
    stat_leaders_cache_key,
    stat_leaders_url,
    team_stats_cache_key,
    team_stats_url,
    teams_cache_key,
    teams_url,
    transactions_cache_key,
    transactions_url,
    venue_url,
    venues_cache_key,
    venues_url,
    win_probability_cache_key,
    win_probability_url,
)
from polars_baseball._season import coerce_datestring, most_recent_season
from polars_baseball.enums.mlb import MlbRosterType, MlbStatsGroup, resolve_group, resolve_roster_type
from polars_baseball.exceptions import InvalidParameterError, UpstreamParseError
from polars_baseball.gateways.film_room import FilmRoomGateway
from polars_baseball.gateways.mlb import MlbStatsGateway
from polars_baseball.parsers.film_room import parse_film_room_search
from polars_baseball.parsers.mlb import (
    MLBApiParser,
    parse_mlb_boxscore,
    parse_mlb_boxscore_stats,
    parse_mlb_divisions,
    parse_mlb_draft,
    parse_mlb_game_feed_live,
    parse_mlb_game_highlights,
    parse_mlb_game_linescore,
    parse_mlb_leagues,
    parse_mlb_people,
    parse_mlb_people_awards,
    parse_mlb_pitch_arsenal,
    parse_mlb_play_by_play,
    parse_mlb_player_stats,
    parse_mlb_roster,
    parse_mlb_schedule,
    parse_mlb_stat_leaders,
    parse_mlb_team_stats,
    parse_mlb_teams,
    parse_mlb_transactions,
    parse_mlb_venues,
    parse_mlb_win_probability,
)
from polars_baseball.parsers.pipeline import MLBPipelineParser
from polars_baseball.parsers.standings import parse_standings_payload

if TYPE_CHECKING:
    from polars_baseball.client import BaseballClient

logger = logging.getLogger(__name__)

_STANDINGS_URL = f"{STATS_API_ROOT}/standings"
_PRE_DEAD_BALL_START = MLB_FIRST_YEAR
_VALID_PROSPECT_TYPES = frozenset({"batters", "pitchers"})


# Film room query helpers
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


def _validate_film_room_params(
    player_ids: list[int] | int | None,
    team_ids: list[int] | int | None,
    seasons: list[int] | int | None,
    date_range: Sequence[str | date | datetime] | None,
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

    _validate_date_range(date_range)

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
        date_range: Sequence[str | date | datetime] | None = None,
        event_types: list[str] | str | None = None,
        pitch_types: list[str] | str | None = None,
        min_exit_velocity: float | None = None,
        max_exit_velocity: float | None = None,
        min_distance: int | None = None,
        max_distance: int | None = None,
        query: str | None = None,
    ) -> str:
        if query is not None and query.strip():
            return query.strip()

        norm_dates = _validate_date_range(date_range)
        clauses: list[str] = []

        for c in (
            _build_int_clause("PlayerID", player_ids),
            _build_int_clause("TeamID", team_ids),
            _build_int_clause("Season", seasons),
            f'Date = ["{norm_dates[0]}", "{norm_dates[1]}"]' if norm_dates else None,
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
        date_range=cast(Sequence[str | date | datetime] | None, kw.get("date_range")),
        event_types=cast(list[str] | str | None, kw.get("event_types")),
        pitch_types=cast(list[str] | str | None, kw.get("pitch_types")),
        min_exit_velocity=cast(float | None, kw.get("min_exit_velocity")),
        max_exit_velocity=cast(float | None, kw.get("max_exit_velocity")),
        min_distance=cast(int | None, kw.get("min_distance")),
        max_distance=cast(int | None, kw.get("max_distance")),
        query=cast(str | None, kw.get("query")),
    )
    return generate_cache_key(FILM_ROOM_GRAPHQL_URL, {"query": query_str, "limit": limit})


def _validate_date_format(val: str | None, name: str) -> None:
    if val is not None and not re.match(r"^\d{4}-\d{2}-\d{2}$", val):
        raise InvalidParameterError(f"Invalid format for parameter {name}. Must be YYYY-MM-DD.")


def _validate_id_param(val: int | None, name: str) -> None:
    if val is not None and val <= 0:
        raise InvalidParameterError(f"{name} must be a positive integer.")


def _validate_transactions_filters(
    c_date: str | None,
    s_date: str | None,
    e_date: str | None,
    team_id: int | None,
    player_id: int | None,
    sport_id: int,
) -> None:
    has_any_filter = any(v is not None for v in (c_date, s_date, e_date, team_id, player_id))
    if not has_any_filter:
        raise InvalidParameterError(
            "Must specify at least one filter: date, start_date/end_date, team_id, or player_id."
        )
    if c_date is not None and (s_date is not None or e_date is not None):
        raise InvalidParameterError("Provide either date or start_date/end_date, not both.")
    if sport_id <= 0:
        raise InvalidParameterError("sport_id must be a positive integer.")
    _validate_id_param(team_id, "team_id")
    _validate_id_param(player_id, "player_id")
    _validate_date_format(c_date, "date")
    _validate_date_format(s_date, "start_date")
    _validate_date_format(e_date, "end_date")


def _validate_venue_ids(venue_ids: int | list[int] | None) -> None:
    if isinstance(venue_ids, int):
        if venue_ids <= 0:
            raise InvalidParameterError("venue_ids must be a positive integer.")
    elif isinstance(venue_ids, list):
        for v in venue_ids:
            if not isinstance(v, int) or v <= 0:
                raise InvalidParameterError("All venue IDs in list must be positive integers.")


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


class MlbClient:
    """Namespaced MLB Stats API client."""

    def __init__(self, client: BaseballClient) -> None:
        self._client = client

    # -------------------------------------------------------------------------
    # Schedule & Calendar
    # -------------------------------------------------------------------------

    async def schedule(
        self,
        season: int | None = None,
        date: date | str | None = None,
        team_id: int | None = None,
        hydrate: str | None = None,
        force_update: bool = False,
    ) -> pl.DataFrame:
        """Fetch MLB schedule."""
        coerced_date = coerce_datestring(date)
        if season is None and coerced_date is None:
            raise InvalidParameterError("Either season or date must be provided.")
        if season is not None and coerced_date is not None:
            raise InvalidParameterError("Cannot specify both season and date.")
        if season is not None and (season < MLB_FIRST_YEAR or season > most_recent_season() + 1):
            raise InvalidParameterError(f"Invalid season: {season}.")
        if coerced_date is not None and not re.match(r"^\d{4}-\d{2}-\d{2}$", coerced_date):
            raise InvalidParameterError("date must be in YYYY-MM-DD format.")
        if team_id is not None and team_id <= 0:
            raise InvalidParameterError("team_id must be a positive integer.")

        params: dict[str, object] = {"sportId": MLB_DEFAULT_SPORT_ID}
        if season is not None:
            params["season"] = season
        if coerced_date is not None:
            params["date"] = coerced_date
        if team_id is not None:
            params["teamId"] = team_id
        if hydrate is not None:
            params["hydrate"] = hydrate

        key = schedule_cache_key(season=season, date=coerced_date, team_id=team_id, hydrate=hydrate)
        return await MlbStatsGateway(self._client).fetch(
            schedule_url(),
            params,
            "Failed to fetch or parse MLB schedule data",
            parse_mlb_schedule,
            use_cache=True,
            max_age=MLB_CACHE_MAX_AGE,
            force_update=force_update,
            cache_key=key,
        )

    async def postseason_schedule(self, season: int, force_update: bool = False) -> pl.DataFrame:
        """Fetch MLB postseason schedule."""
        if season < MLB_FIRST_YEAR or season > most_recent_season() + 1:
            raise InvalidParameterError(f"Invalid season: {season}.")

        params: dict[str, object] = {
            "gameType": MLB_POSTSEASON_GAME_TYPE,
            "sportId": MLB_DEFAULT_SPORT_ID,
            "season": season,
        }
        key = postseason_cache_key(season=season)
        return await MlbStatsGateway(self._client).fetch(
            schedule_url(),
            params,
            "Failed to fetch or parse MLB postseason schedule data",
            parse_mlb_schedule,
            use_cache=True,
            max_age=MLB_CACHE_MAX_AGE,
            force_update=force_update,
            cache_key=key,
        )

    # -------------------------------------------------------------------------
    # Game Data
    # -------------------------------------------------------------------------

    async def game_boxscore(self, game_pk: int, force_update: bool = False) -> pl.DataFrame:
        """Fetch MLB game boxscore."""
        if game_pk <= 0:
            raise InvalidParameterError("game_pk must be a positive integer.")
        url = boxscore_url(game_pk)
        key = boxscore_cache_key(game_pk=game_pk)
        return await MlbStatsGateway(self._client).fetch(
            url,
            None,
            "Failed to fetch or parse MLB game boxscore",
            lambda d: parse_mlb_boxscore(d, game_pk),
            use_cache=True,
            max_age=MLB_CACHE_MAX_AGE,
            force_update=force_update,
            cache_key=key,
        )

    async def game_boxscore_stats(self, game_pk: int, force_update: bool = False) -> pl.DataFrame:
        """Fetch MLB game boxscore stats."""
        if game_pk <= 0:
            raise InvalidParameterError("game_pk must be a positive integer.")
        url = boxscore_url(game_pk)
        key = boxscore_stats_cache_key(game_pk=game_pk)
        return await MlbStatsGateway(self._client).fetch(
            url,
            None,
            "Failed to fetch or parse MLB game boxscore stats",
            lambda d: parse_mlb_boxscore_stats(d, game_pk),
            use_cache=True,
            max_age=MLB_CACHE_MAX_AGE,
            force_update=force_update,
            cache_key=key,
        )

    async def game_linescore(
        self,
        game_pk: int,
        force_update: bool = False,
        cache_max_age: timedelta | None = MLB_LIVE_ENDPOINT_CACHE_MAX_AGE,
    ) -> pl.DataFrame:
        """Fetch MLB game linescore."""
        if game_pk <= 0:
            raise InvalidParameterError("game_pk must be a positive integer.")
        url = linescore_url(game_pk)
        key = linescore_cache_key(game_pk=game_pk)
        return await MlbStatsGateway(self._client).fetch(
            url,
            None,
            "Failed to fetch or parse MLB game linescore",
            lambda d: parse_mlb_game_linescore(d, game_pk),
            use_cache=True,
            max_age=cache_max_age,
            force_update=force_update,
            cache_key=key,
        )

    async def game_play_by_play(
        self,
        game_pk: int,
        win_probability: bool = False,
        force_update: bool = False,
    ) -> pl.DataFrame:
        """Fetch MLB game play-by-play events."""
        if game_pk <= 0:
            raise InvalidParameterError("game_pk must be a positive integer.")
        if win_probability:
            url = win_probability_url(game_pk)
            key = win_probability_cache_key(game_pk=game_pk)
            return await MlbStatsGateway(self._client).fetch_payload(
                url,
                None,
                "Failed to fetch or parse MLB win probability data",
                lambda d: parse_mlb_win_probability(d, game_pk),
                use_cache=True,
                max_age=MLB_CACHE_MAX_AGE,
                force_update=force_update,
                cache_key=key,
            )
        url = play_by_play_url(game_pk)
        key = play_by_play_cache_key(game_pk=game_pk)
        return await MlbStatsGateway(self._client).fetch(
            url,
            None,
            "Failed to fetch or parse MLB game play-by-play",
            lambda d: parse_mlb_play_by_play(d, game_pk),
            use_cache=True,
            max_age=MLB_CACHE_MAX_AGE,
            force_update=force_update,
            cache_key=key,
        )

    async def game_win_probability(self, game_pk: int, force_update: bool = False) -> pl.DataFrame:
        """Fetch MLB game win probability."""
        if game_pk <= 0:
            raise InvalidParameterError("game_pk must be a positive integer.")
        return await self.game_play_by_play(game_pk=game_pk, win_probability=True, force_update=force_update)

    async def game_feed_live(self, game_pk: int, force_update: bool = False) -> pl.DataFrame:
        """Fetch MLB live game feed."""
        if game_pk <= 0:
            raise InvalidParameterError("game_pk must be a positive integer.")
        url = live_feed_url(game_pk)
        key = live_feed_cache_key(game_pk=game_pk)
        return await MlbStatsGateway(self._client).fetch(
            url,
            None,
            "Failed to fetch or parse MLB live feed",
            lambda d: parse_mlb_game_feed_live(d, game_pk),
            use_cache=True,
            max_age=MLB_LIVE_ENDPOINT_CACHE_MAX_AGE,
            force_update=force_update,
            cache_key=key,
        )

    async def game_highlights(self, game_pk: int, force_update: bool = False) -> pl.DataFrame:
        """Fetch MLB game highlights."""
        if game_pk <= 0:
            raise InvalidParameterError("game_pk must be a positive integer.")
        url = game_content_url(game_pk)
        key = game_highlights_cache_key(game_pk=game_pk)
        return await MlbStatsGateway(self._client).fetch(
            url,
            None,
            "Failed to fetch or parse MLB game highlights",
            lambda d: parse_mlb_game_highlights(d, game_pk),
            use_cache=True,
            max_age=MLB_CACHE_MAX_AGE,
            force_update=force_update,
            cache_key=key,
        )

    mlb_game_highlights = game_highlights

    # -------------------------------------------------------------------------
    # People, Stats & Roster
    # -------------------------------------------------------------------------

    async def people(self, person_ids: list[int] | int, force_update: bool = False) -> pl.DataFrame:
        """Fetch MLB people metadata."""
        if not person_ids:
            raise InvalidParameterError("person_ids must not be empty.")
        if isinstance(person_ids, list):
            for pid in person_ids:
                if not isinstance(pid, int) or pid <= 0:
                    raise InvalidParameterError(f"Invalid player ID: {pid}. Must be positive integer.")
            ids_str = ",".join(map(str, person_ids))
        else:
            if not isinstance(person_ids, int) or person_ids <= 0:
                raise InvalidParameterError(f"Invalid player ID: {person_ids}. Must be positive integer.")
            ids_str = str(person_ids)

        key = people_cache_key(person_ids=person_ids)
        return await MlbStatsGateway(self._client).fetch(
            people_url(),
            {"personIds": ids_str},
            "Failed to fetch or parse MLB people data",
            parse_mlb_people,
            use_cache=True,
            max_age=MLB_CACHE_MAX_AGE,
            force_update=force_update,
            cache_key=key,
        )

    async def people_awards(self, person_id: int, force_update: bool = False) -> pl.DataFrame:
        """Fetch official MLB award timeline rows for a single person."""
        if person_id <= 0:
            raise InvalidParameterError("person_id must be a positive integer.")
        url = people_awards_url(person_id)
        key = people_awards_cache_key(person_id=person_id)
        return await MlbStatsGateway(self._client).fetch(
            url,
            None,
            "Failed to fetch or parse MLB people awards data",
            lambda d: parse_mlb_people_awards(d, person_id),
            use_cache=True,
            max_age=MLB_CACHE_MAX_AGE,
            force_update=force_update,
            cache_key=key,
        )

    async def player_stats(
        self,
        person_id: int,
        group: str | MlbStatsGroup = "hitting",
        stats_type: str = MLB_DEFAULT_STATS_TYPE,
        season: int | None = None,
        start_date: date | str | None = None,
        end_date: date | str | None = None,
        force_update: bool = False,
    ) -> pl.DataFrame:
        """Fetch player stats from the MLB Stats API for a given stat group."""
        s_date = coerce_datestring(start_date)
        e_date = coerce_datestring(end_date)
        if person_id <= 0:
            raise InvalidParameterError("person_id must be a positive integer.")
        resolved_grp = resolve_group(group)
        if not stats_type:
            raise InvalidParameterError("stats_type must be a non-empty string.")
        if season is not None and (season < MLB_FIRST_YEAR or season > most_recent_season() + 1):
            raise InvalidParameterError(f"Invalid season: {season}.")
        if s_date is not None and not re.match(r"^\d{4}-\d{2}-\d{2}$", s_date):
            raise InvalidParameterError("start_date must be in YYYY-MM-DD format.")
        if e_date is not None and not re.match(r"^\d{4}-\d{2}-\d{2}$", e_date):
            raise InvalidParameterError("end_date must be in YYYY-MM-DD format.")

        url = people_stats_url(person_id)
        params: dict[str, object] = {"stats": stats_type, "group": resolved_grp}
        if season is not None:
            params["season"] = season
        if s_date is not None:
            params["startDate"] = s_date
        if e_date is not None:
            params["endDate"] = e_date

        key = player_stats_cache_key(
            person_id=person_id,
            group=resolved_grp,
            stats_type=stats_type,
            season=season,
            start_date=s_date,
            end_date=e_date,
        )
        return await MlbStatsGateway(self._client).fetch(
            url,
            params,
            "Failed to fetch or parse MLB player stats",
            lambda d: parse_mlb_player_stats(d, person_id, resolved_grp, stats_type),
            use_cache=True,
            max_age=MLB_CACHE_MAX_AGE,
            force_update=force_update,
            cache_key=key,
        )

    async def pitch_arsenal(
        self,
        person_id: int,
        season: int,
        force_update: bool = False,
    ) -> pl.DataFrame:
        """Fetch pitcher pitch arsenal statistics from the MLB Stats API."""
        if person_id <= 0:
            raise InvalidParameterError("person_id must be a positive integer.")
        if season < MLB_FIRST_YEAR or season > most_recent_season() + 1:
            raise InvalidParameterError(f"Invalid season: {season}.")

        url = people_stats_url(person_id)
        params: dict[str, object] = {"stats": MLB_PITCH_ARSENAL_STATS, "season": season}
        key = pitch_arsenal_cache_key(person_id=person_id, season=season)
        return await MlbStatsGateway(self._client).fetch(
            url,
            params,
            "Failed to fetch or parse MLB pitch arsenal stats",
            lambda d: parse_mlb_pitch_arsenal(d, person_id, season),
            use_cache=True,
            max_age=MLB_CACHE_MAX_AGE,
            force_update=force_update,
            cache_key=key,
        )

    async def roster(
        self,
        team_id: int,
        season: int | None = None,
        roster_type: str | MlbRosterType = MLB_ACTIVE_ROSTER_TYPE,
        force_update: bool = False,
    ) -> pl.DataFrame:
        """Fetch team roster from the MLB Stats API."""
        if team_id <= 0:
            raise InvalidParameterError("team_id must be a positive integer.")
        if season is not None and (season < MLB_FIRST_YEAR or season > most_recent_season() + 1):
            raise InvalidParameterError(f"Invalid season: {season}.")
        resolved_type = resolve_roster_type(roster_type)

        url = roster_url(team_id)
        params: dict[str, object] = {"rosterType": resolved_type}
        if season is not None:
            params["season"] = season

        key = roster_cache_key(team_id=team_id, season=season, roster_type=resolved_type)
        return await MlbStatsGateway(self._client).fetch(
            url,
            params,
            "Failed to fetch or parse MLB roster data",
            lambda d: parse_mlb_roster(d, team_id),
            use_cache=True,
            max_age=MLB_CACHE_MAX_AGE,
            force_update=force_update,
            cache_key=key,
        )

    # -------------------------------------------------------------------------
    # Team & League Taxonomy
    # -------------------------------------------------------------------------

    async def teams(
        self,
        season: int | None = None,
        league_id: int | None = None,
        sport_id: int = MLB_DEFAULT_SPORT_ID,
        force_update: bool = False,
    ) -> pl.DataFrame:
        """Fetch MLB team information from the Stats API."""
        if season is not None:
            if season <= 0:
                raise InvalidParameterError("season must be a positive integer.")
            if season < MLB_FIRST_YEAR or season > most_recent_season() + 1:
                raise InvalidParameterError(f"Invalid season: {season}.")
        if sport_id <= 0:
            raise InvalidParameterError("sport_id must be a positive integer.")

        url = teams_url()
        params: dict[str, object] = {"sportId": sport_id}
        if season is not None:
            params["season"] = season
        if league_id is not None:
            params["leagueId"] = league_id

        key = teams_cache_key(season=season, league_id=league_id, sport_id=sport_id)
        return await MlbStatsGateway(self._client).fetch(
            url,
            params,
            "Failed to fetch or parse MLB teams data",
            lambda d: parse_mlb_teams(d, season),
            use_cache=True,
            max_age=MLB_CACHE_MAX_AGE,
            force_update=force_update,
            cache_key=key,
        )

    async def divisions(self, sport_id: int = MLB_DEFAULT_SPORT_ID, force_update: bool = False) -> pl.DataFrame:
        """Fetch official MLB division dimension metadata from the Stats API."""
        if sport_id <= 0:
            raise InvalidParameterError("sport_id must be a positive integer.")
        key = divisions_cache_key(sport_id=sport_id)
        return await MlbStatsGateway(self._client).fetch(
            divisions_url(),
            {"sportId": sport_id},
            "Failed to fetch or parse MLB divisions data",
            parse_mlb_divisions,
            use_cache=True,
            max_age=MLB_CACHE_MAX_AGE,
            force_update=force_update,
            cache_key=key,
        )

    async def leagues(self, sport_id: int = MLB_DEFAULT_SPORT_ID, force_update: bool = False) -> pl.DataFrame:
        """Fetch official MLB league dimension metadata from the Stats API."""
        if sport_id <= 0:
            raise InvalidParameterError("sport_id must be a positive integer.")
        key = leagues_cache_key(sport_id=sport_id)
        return await MlbStatsGateway(self._client).fetch(
            leagues_url(),
            {"sportId": sport_id},
            "Failed to fetch or parse MLB leagues data",
            parse_mlb_leagues,
            use_cache=True,
            max_age=MLB_CACHE_MAX_AGE,
            force_update=force_update,
            cache_key=key,
        )

    async def team_stats(
        self,
        team_id: int,
        season: int | None = None,
        group: str = MLB_DEFAULT_STATS_GROUP,
        stats_type: str = MLB_DEFAULT_STATS_TYPE,
        force_update: bool = False,
    ) -> pl.DataFrame:
        """Fetch aggregate season stats for an MLB team."""
        if team_id <= 0:
            raise InvalidParameterError("team_id must be a positive integer.")
        if season is not None and (season < MLB_FIRST_YEAR or season > most_recent_season() + 1):
            raise InvalidParameterError(f"Invalid season: {season}.")
        resolved_grp = resolve_group(group)
        if not stats_type:
            raise InvalidParameterError("stats_type must be a non-empty string.")

        url = team_stats_url(team_id)
        params: dict[str, object] = {"group": resolved_grp, "stats": stats_type}
        if season is not None:
            params["season"] = season

        key = team_stats_cache_key(team_id=team_id, season=season, group=resolved_grp, stats_type=stats_type)
        return await MlbStatsGateway(self._client).fetch(
            url,
            params,
            "Failed to fetch or parse MLB team stats",
            lambda d: parse_mlb_team_stats(d, team_id, resolved_grp),
            use_cache=True,
            max_age=MLB_CACHE_MAX_AGE,
            force_update=force_update,
            cache_key=key,
        )

    async def stat_leaders(
        self,
        categories: list[str] | None = None,
        season: int | None = None,
        stat_group: str | None = None,
        limit: int = 10,
        force_update: bool = False,
        leader_categories: str | list[str] | None = None,
    ) -> pl.DataFrame:
        """Fetch MLB stat leaders for one or more statistical categories."""
        raw_cats = leader_categories if leader_categories is not None else categories
        cats: list[str] | None = [raw_cats] if isinstance(raw_cats, str) else raw_cats
        if cats is not None:
            cats = [c for c in cats if c]

        if not cats:
            raise InvalidParameterError("leader_categories must not be empty.")
        if season is not None and (season < MLB_FIRST_YEAR or season > most_recent_season() + 1):
            raise InvalidParameterError(f"Invalid season: {season}.")
        if limit <= 0:
            raise InvalidParameterError("limit must be a positive integer.")

        resolved_season = season if season is not None else most_recent_season()
        params: dict[str, object] = {
            "leaderCategories": ",".join(cats),
            "limit": limit,
            "season": resolved_season,
        }
        if stat_group is not None:
            params["statGroup"] = stat_group

        key = stat_leaders_cache_key(season=resolved_season, categories=cats, limit=limit, stat_group=stat_group)
        return await MlbStatsGateway(self._client).fetch(
            stat_leaders_url(),
            params,
            "Failed to fetch or parse MLB stat leaders",
            lambda d: parse_mlb_stat_leaders(d, resolved_season, stat_group),
            use_cache=True,
            max_age=MLB_CACHE_MAX_AGE,
            force_update=force_update,
            cache_key=key,
        )

    async def standings(self, season: int | None = None, force_update: bool = False) -> pl.DataFrame:
        """Fetch division standings from the MLB Stats API."""
        if season is None:
            season = most_recent_season()
        if season < _PRE_DEAD_BALL_START:
            raise InvalidParameterError(
                f"This query currently only returns standings until the {_PRE_DEAD_BALL_START} season."
            )
        return await MlbStatsGateway(self._client).fetch(
            _STANDINGS_URL,
            params={"leagueId": "103,104", "season": season},
            error_msg="Failed to fetch or parse standings from MLB Stats API",
            parser=lambda payload: parse_standings_payload(payload, season),
            use_cache=True,
            force_update=force_update,
        )

    # -------------------------------------------------------------------------
    # Draft, Transactions & Venues
    # -------------------------------------------------------------------------

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
        key = draft_cache_key(year=year)
        df = await MlbStatsGateway(self._client).fetch(
            url,
            None,
            "Failed to fetch or parse MLB draft data",
            lambda d: parse_mlb_draft(d, year),
            use_cache=True,
            max_age=MLB_CACHE_MAX_AGE,
            force_update=force_update,
            cache_key=key,
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
        c_date = coerce_datestring(date)
        s_date = coerce_datestring(start_date)
        e_date = coerce_datestring(end_date)
        _validate_transactions_filters(c_date, s_date, e_date, team_id, player_id, sport_id)

        params: dict[str, object] = {"sportId": sport_id}
        if c_date:
            params["date"] = c_date
        if s_date:
            params["startDate"] = s_date
        if e_date:
            params["endDate"] = e_date
        if team_id is not None:
            params["teamId"] = team_id
        if player_id is not None:
            params["playerId"] = player_id

        key = transactions_cache_key(
            date=c_date,
            start_date=s_date,
            end_date=e_date,
            team_id=team_id,
            player_id=player_id,
            sport_id=sport_id,
        )
        return await MlbStatsGateway(self._client).fetch(
            transactions_url(),
            params,
            "Failed to fetch or parse MLB transactions data",
            parse_mlb_transactions,
            use_cache=True,
            max_age=MLB_CACHE_MAX_AGE,
            force_update=force_update,
            cache_key=key,
        )

    async def venues(
        self,
        venue_ids: int | list[int] | None = None,
        force_update: bool = False,
    ) -> pl.DataFrame:
        """Fetch MLB venue details."""
        _validate_venue_ids(venue_ids)
        if isinstance(venue_ids, int):
            url = venue_url(str(venue_ids))
            params: dict[str, object] = {}
        elif isinstance(venue_ids, list):
            url = venues_url()
            params = {"venueIds": ",".join(map(str, venue_ids))}
        else:
            url = venues_url()
            params = {}

        key = venues_cache_key(venue_ids=venue_ids)
        return await MlbStatsGateway(self._client).fetch(
            url,
            params,
            "Failed to fetch or parse MLB venues data",
            parse_mlb_venues,
            use_cache=True,
            max_age=MLB_CACHE_MAX_AGE,
            force_update=force_update,
            cache_key=key,
        )

    # -------------------------------------------------------------------------
    # Film Room Search
    # -------------------------------------------------------------------------

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

        key = generate_cache_key(FILM_ROOM_GRAPHQL_URL, {"query": query_str, "limit": limit})
        return await FilmRoomGateway(self._client).fetch_search(
            query_str=query_str,
            limit=limit,
            error_msg="Failed to fetch or parse MLB Film Room search results",
            parser=parse_film_room_search,
            use_cache=True,
            max_age=MLB_CACHE_MAX_AGE,
            force_update=force_update,
            cache_key=key,
        )

    # -------------------------------------------------------------------------
    # Prospects (Top Prospects & Pipeline Rankings)
    # -------------------------------------------------------------------------

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
            html_str = await MlbStatsGateway(self._client).fetch_text(
                url, f"MLB pipeline prospects returned empty response for: {url}"
            )
            return MLBPipelineParser().parse(html_str)

        key = generate_cache_key(
            "milb/prospect_rankings", {"list_type": list_type_clean, "year": "current" if year is None else str(year)}
        )
        return await self._client.cache.get_or_fetch(key, _fetch, max_age=MLB_CACHE_MAX_AGE, force_update=force_update)

    async def resolve_team_id(self, team_name: str) -> int:
        """Resolve an MLB team display name to a Stats API team id."""
        clean_name = team_name.replace(" ", "").replace("-", "").lower()
        teams_df = await self.teams(season=most_recent_season())
        norm_expr = pl.col("teamName").str.to_lowercase().str.replace_all(r"[ -]", "")
        filtered = teams_df.filter(norm_expr == clean_name)
        if filtered.is_empty():
            raise InvalidParameterError(f"Could not resolve team name: {team_name}")
        team_id = filtered["id"][0]
        if team_id is None or team_id == -1:
            raise InvalidParameterError(f"Could not resolve team name: {team_name}")
        return int(team_id)

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
            html_str = await MlbStatsGateway(self._client).fetch_text(url, "MLB top prospects returned empty response.")
            dfs = MLBApiParser().parse_tables(html_str)
            return _clean_prospect_df(_extract_prospect_df(dfs, player_type))

        clean_team = "league" if team_name is None else team_name.lower().strip()
        clean_type = "all" if player_type is None else player_type.lower().strip()
        key = generate_cache_key("mlb/top_prospects", {"team": clean_team, "type": clean_type})
        return await self._client.cache.get_or_fetch(key, _fetch, max_age=MLB_CACHE_MAX_AGE, force_update=force_update)

    mlb_schedule = schedule
    mlb_postseason_schedule = postseason_schedule
    mlb_game_boxscore = game_boxscore
    mlb_game_boxscore_stats = game_boxscore_stats
    mlb_game_linescore = game_linescore
    mlb_game_play_by_play = game_play_by_play
    mlb_game_win_probability = game_win_probability
    mlb_game_feed_live = game_feed_live
    mlb_people = people
    mlb_people_awards = people_awards
    mlb_player_stats = player_stats
    mlb_pitch_arsenal = pitch_arsenal
    mlb_roster = roster
    mlb_teams = teams
    mlb_divisions = divisions
    mlb_leagues = leagues
    mlb_team_stats = team_stats
    mlb_stat_leaders = stat_leaders
    mlb_standings = standings
    mlb_draft = draft
    mlb_transactions = transactions
    mlb_venues = venues


def __getattr__(name: str) -> None:
    raise AttributeError(
        f"Top-level function 'polars_baseball.mlb.{name}' was removed. "
        f"Use BaseballClient: `client = BaseballClient(); await client.mlb.{name}(...)`."
    )


__all__ = [
    "FilmRoomQueryBuilder",
    "MlbClient",
    "film_room_cache_key",
]
