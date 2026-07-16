from datetime import timedelta
from typing import Final

from polars_baseball._cache import CacheCallArgs, generate_cache_key
from polars_baseball._config import STATS_API_ROOT
from polars_baseball._json_types import JsonObject as JsonObject

MLB_CACHE_MAX_AGE: Final[timedelta] = timedelta(days=1)
MLB_LIVE_ENDPOINT_CACHE_MAX_AGE: Final[timedelta] = timedelta(seconds=10)
MLB_DEFAULT_SPORT_ID: Final[int] = 1
MLB_POSTSEASON_GAME_TYPE: Final[str] = "P"
MLB_ACTIVE_ROSTER_TYPE: Final[str] = "active"
MLB_DEFAULT_STATS_TYPE: Final[str] = "season"
MLB_DEFAULT_STATS_GROUP: Final[str] = "hitting"
MLB_DEFAULT_LEADER_LIMIT: Final[int] = 10
MLB_PITCH_ARSENAL_STATS: Final[str] = "pitchArsenal"

_PEOPLE_URL: Final[str] = f"{STATS_API_ROOT}/people"
_SCHEDULE_URL: Final[str] = f"{STATS_API_ROOT}/schedule"
_ROSTER_URL_TEMPLATE: Final[str] = f"{STATS_API_ROOT}/teams/{{}}/roster"
_PEOPLE_STATS_URL_TEMPLATE: Final[str] = f"{STATS_API_ROOT}/people/{{}}/stats"
_PEOPLE_AWARDS_URL_TEMPLATE: Final[str] = f"{STATS_API_ROOT}/people/{{}}/awards"
_BOXSCORE_URL_TEMPLATE: Final[str] = f"{STATS_API_ROOT}/game/{{}}/boxscore"
_LINESCORE_URL_TEMPLATE: Final[str] = f"{STATS_API_ROOT}/game/{{}}/linescore"
_TEAM_STATS_URL_TEMPLATE: Final[str] = f"{STATS_API_ROOT}/teams/{{}}/stats"
_DIVISIONS_URL: Final[str] = f"{STATS_API_ROOT}/divisions"
_LEAGUES_URL: Final[str] = f"{STATS_API_ROOT}/leagues"
_TEAMS_URL: Final[str] = f"{STATS_API_ROOT}/teams"
_STAT_LEADERS_URL: Final[str] = f"{STATS_API_ROOT}/stats/leaders"
_DRAFT_URL_TEMPLATE: Final[str] = f"{STATS_API_ROOT}/draft/{{}}"
_PLAY_BY_PLAY_URL_TEMPLATE: Final[str] = f"{STATS_API_ROOT}/game/{{}}/playByPlay"
_WIN_PROBABILITY_URL_TEMPLATE: Final[str] = f"{STATS_API_ROOT}/game/{{}}/winProbability"
_LIVE_FEED_URL_TEMPLATE: Final[str] = f"{STATS_API_ROOT[:-3]}/v1.1/game/{{}}/feed/live"
_TRANSACTIONS_URL: Final[str] = f"{STATS_API_ROOT}/transactions"
_VENUES_URL: Final[str] = f"{STATS_API_ROOT}/venues"
_VENUE_URL_TEMPLATE: Final[str] = f"{STATS_API_ROOT}/venues/{{}}"


def people_url() -> str:
    return _PEOPLE_URL


def schedule_url() -> str:
    return _SCHEDULE_URL


def roster_url(team_id: int) -> str:
    return _ROSTER_URL_TEMPLATE.format(team_id)


def people_stats_url(person_id: int) -> str:
    return _PEOPLE_STATS_URL_TEMPLATE.format(person_id)


def people_awards_url(person_id: int) -> str:
    return _PEOPLE_AWARDS_URL_TEMPLATE.format(person_id)


def boxscore_url(game_pk: int) -> str:
    return _BOXSCORE_URL_TEMPLATE.format(game_pk)


def linescore_url(game_pk: int) -> str:
    return _LINESCORE_URL_TEMPLATE.format(game_pk)


def team_stats_url(team_id: int) -> str:
    return _TEAM_STATS_URL_TEMPLATE.format(team_id)


def divisions_url() -> str:
    return _DIVISIONS_URL


def leagues_url() -> str:
    return _LEAGUES_URL


def teams_url() -> str:
    return _TEAMS_URL


def stat_leaders_url() -> str:
    return _STAT_LEADERS_URL


def draft_url(year: int) -> str:
    return _DRAFT_URL_TEMPLATE.format(year)


def play_by_play_url(game_pk: int) -> str:
    return _PLAY_BY_PLAY_URL_TEMPLATE.format(game_pk)


def win_probability_url(game_pk: int) -> str:
    return _WIN_PROBABILITY_URL_TEMPLATE.format(game_pk)


def live_feed_url(game_pk: int) -> str:
    return _LIVE_FEED_URL_TEMPLATE.format(game_pk)


def transactions_url() -> str:
    return _TRANSACTIONS_URL


def venues_url() -> str:
    return _VENUES_URL


def venue_url(venue_ids: str) -> str:
    return _VENUE_URL_TEMPLATE.format(venue_ids)


def people_cache_key(call: CacheCallArgs) -> str:
    person_ids = call.argument("person_ids", object)
    if not isinstance(person_ids, int | list):
        raise TypeError(f"person_ids must be int or list, got {type(person_ids).__name__}")
    ids_str = ",".join(map(str, person_ids)) if isinstance(person_ids, list) else str(person_ids)
    return generate_cache_key(people_url(), {"personIds": ids_str})


def people_awards_cache_key(call: CacheCallArgs) -> str:
    person_id = call.argument("person_id", int)
    return generate_cache_key(people_awards_url(person_id), {})


def schedule_cache_key(call: CacheCallArgs) -> str:
    season = call.argument("season", int)
    date = call.argument("date", str, None)
    team_id = call.argument("team_id", int, None)
    hydrate = call.argument("hydrate", str, None)
    params: dict[str, object] = {"sportId": MLB_DEFAULT_SPORT_ID}
    if season is not None:
        params["season"] = season
    if date is not None:
        params["date"] = date
    if team_id is not None:
        params["teamId"] = team_id
    if hydrate is not None:
        params["hydrate"] = hydrate
    return generate_cache_key(schedule_url(), params)


def postseason_cache_key(call: CacheCallArgs) -> str:
    season = call.argument("season", int, None)
    params: dict[str, object] = {
        "gameType": MLB_POSTSEASON_GAME_TYPE,
        "sportId": MLB_DEFAULT_SPORT_ID,
        "season": season,
    }
    return generate_cache_key(schedule_url(), params)


def roster_cache_key(call: CacheCallArgs) -> str:
    team_id = call.argument("team_id", int)
    season = call.argument("season", int)
    roster_type = call.argument("roster_type", str, MLB_ACTIVE_ROSTER_TYPE)
    params: dict[str, object] = {"rosterType": roster_type}
    if season is not None:
        params["season"] = season
    return generate_cache_key(roster_url(team_id), params)


def player_stats_cache_key(call: CacheCallArgs) -> str:
    person_id = call.argument("person_id", int)
    group = call.argument("group", str)
    stats_type = call.argument("stats_type", str, MLB_DEFAULT_STATS_TYPE)
    season = call.argument("season", int, None)
    start_date = call.argument("start_date", str, None)
    end_date = call.argument("end_date", str, None)
    params: dict[str, object] = {"stats": stats_type, "group": group}
    if season is not None:
        params["season"] = season
    if start_date is not None:
        params["startDate"] = start_date
    if end_date is not None:
        params["endDate"] = end_date
    return generate_cache_key(people_stats_url(person_id), params)


def boxscore_cache_key(call: CacheCallArgs) -> str:
    game_pk = call.argument("game_pk", int)
    return generate_cache_key(boxscore_url(game_pk), {})


def boxscore_stats_cache_key(call: CacheCallArgs) -> str:
    game_pk = call.argument("game_pk", int)
    return generate_cache_key(boxscore_url(game_pk), {"schema": "stats"})


def team_stats_cache_key(call: CacheCallArgs) -> str:
    team_id = call.argument("team_id", int)
    season = call.argument("season", int, None)
    group = call.argument("group", str, MLB_DEFAULT_STATS_GROUP)
    stats_type = call.argument("stats_type", str, MLB_DEFAULT_STATS_TYPE)
    params: dict[str, object] = {"group": group, "stats": stats_type}
    if season is not None:
        params["season"] = season
    return generate_cache_key(team_stats_url(team_id), params)


def divisions_cache_key(call: CacheCallArgs) -> str:
    sport_id = call.argument("sport_id", int, MLB_DEFAULT_SPORT_ID)
    return generate_cache_key(divisions_url(), {"sportId": sport_id})


def leagues_cache_key(call: CacheCallArgs) -> str:
    sport_id = call.argument("sport_id", int, MLB_DEFAULT_SPORT_ID)
    return generate_cache_key(leagues_url(), {"sportId": sport_id})


def teams_cache_key(call: CacheCallArgs) -> str:
    season = call.argument("season", int, None)
    league_id = call.argument("league_id", int, None)
    sport_id = call.argument("sport_id", int, MLB_DEFAULT_SPORT_ID)
    params: dict[str, object] = {"sportId": sport_id}
    if season is not None:
        params["season"] = season
    if league_id is not None:
        params["leagueId"] = league_id
    return generate_cache_key(teams_url(), params)


def stat_leaders_cache_key(call: CacheCallArgs) -> str:
    season = call.argument("season", int)
    categories = call.argument("categories", list)
    limit = call.argument("limit", int, MLB_DEFAULT_LEADER_LIMIT)
    stat_group = call.argument("stat_group", str, None)
    params: dict[str, object] = {
        "leaderCategories": ",".join(categories),
        "limit": limit,
        "season": season,
    }
    if stat_group is not None:
        params["statGroup"] = stat_group
    return generate_cache_key(stat_leaders_url(), params)


def pitch_arsenal_cache_key(call: CacheCallArgs) -> str:
    person_id = call.argument("person_id", int)
    season = call.argument("season", int)
    params: dict[str, object] = {"stats": MLB_PITCH_ARSENAL_STATS, "season": season}
    return generate_cache_key(people_stats_url(person_id), params)


def draft_cache_key(call: CacheCallArgs) -> str:
    year = call.argument("year", int)
    return generate_cache_key(draft_url(year), {})


def play_by_play_cache_key(call: CacheCallArgs) -> str:
    game_pk = call.argument("game_pk", int)
    return generate_cache_key(play_by_play_url(game_pk), {})


def win_probability_cache_key(call: CacheCallArgs) -> str:
    game_pk = call.argument("game_pk", int)
    return generate_cache_key(win_probability_url(game_pk), {})


def live_feed_cache_key(call: CacheCallArgs) -> str:
    game_pk = call.argument("game_pk", int)
    return generate_cache_key(live_feed_url(game_pk), {})


def linescore_cache_key(call: CacheCallArgs) -> str:
    game_pk = call.argument("game_pk", int)
    return generate_cache_key(linescore_url(game_pk), {})


def transactions_cache_key(call: CacheCallArgs) -> str:
    date = call.argument("date", str, None)
    start_date = call.argument("start_date", str, None)
    end_date = call.argument("end_date", str, None)
    sport_id = call.argument("sport_id", int, MLB_DEFAULT_SPORT_ID)
    params: dict[str, object] = {"sportId": sport_id}
    if date:
        params["date"] = date
    if start_date:
        params["startDate"] = start_date
    if end_date:
        params["endDate"] = end_date
    return generate_cache_key(transactions_url(), params)


def venues_cache_key(call: CacheCallArgs) -> str:
    venue_ids = call.argument("venue_ids", object, None)
    if venue_ids is not None and not isinstance(venue_ids, int | list):
        raise TypeError(f"venue_ids must be int or list, got {type(venue_ids).__name__}")
    if isinstance(venue_ids, list):
        ids = ",".join(map(str, venue_ids))
        return generate_cache_key(venues_url(), {"venueIds": ids})
    if venue_ids is not None:
        return generate_cache_key(venue_url(str(venue_ids)), {})
    return generate_cache_key(venues_url(), {})
