import asyncio
import os

import polars as pl

from polars_baseball._cache import CacheCallArgs, cached, generate_cache_key
from polars_baseball._config import (
    RETROSHEET_CONTENTS_URL_TEMPLATE,
    RETROSHEET_EVENT_URL,
    RETROSHEET_GAMELOG_URL,
    RETROSHEET_PARKID_URL,
    RETROSHEET_ROSTER_URL,
    RETROSHEET_SCHEDULE_URL,
    RETROSHEET_SEASON_GAMELOG_URL,
)
from polars_baseball.context import BaseballContext, default_context
from polars_baseball.exceptions import (
    InvalidParameterError,
    ServerError,
)
from polars_baseball.parsers.retrosheet import (
    empty_rosters_frame,
    event_content_row,
    events_frame,
    parse_gamelog_csv,
    parse_park_codes_csv,
    parse_roster_csv,
    parse_schedule_csv,
    parse_season_contents,
)


async def _get_season_contents(season: int, ctx: BaseballContext) -> list[str]:
    url = RETROSHEET_CONTENTS_URL_TEMPLATE.format(season)
    headers = {}
    gh_token = os.getenv("GH_TOKEN", "")
    if gh_token:
        headers["Authorization"] = f"token {gh_token}"

    raw_bytes = await ctx.http.get_text(url, headers=headers)
    if not raw_bytes:
        raise ServerError(f"Season {season} directory not found or empty.")
    return parse_season_contents(raw_bytes, season)


async def events(
    season: int,
    type: str = "regular",
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch Retrosheet event files for a given season.

    Returns one DataFrame with filename and raw event file content.
    Edge Cases: type parameter selects file extensions (".EVA"/".EVN" for "regular",
    post-season variants for "post", ".AS.EVE" for "asg"); raises InvalidParameterError
    for unknown types and ServerError if no event files are found.
    """
    ctx = context or default_context()
    files = await _get_season_contents(season, ctx)
    file_extension: tuple[str, ...]
    if type == "regular":
        file_extension = (".EVA", ".EVN")
    elif type == "post":
        file_extension = ("CS.EVE", "D1.EVE", "D2.EVE", "W1.EVE", "W2.EVE", "WS.EVE")
    elif type == "asg":
        file_extension = ("AS.EVE",)
    else:
        raise InvalidParameterError(f"Illegal type argument {type}, the valid types are: 'regular', 'post', and 'asg'.")

    season_events = [t for t in files if t.endswith(file_extension)]
    if not season_events:
        raise ServerError(f"Event files not available for {season}")

    async def _fetch_event(filename: str) -> dict[str, object] | None:
        url = RETROSHEET_EVENT_URL.format(season, filename)
        raw = await ctx.http.get_text(url)
        if not raw:
            return None
        return event_content_row(season, type, filename, raw)

    results = await asyncio.gather(*[_fetch_event(f) for f in season_events])
    rows = [row for row in results if row is not None]
    return events_frame(rows)


def _rosters_cache_key(call: CacheCallArgs) -> str:
    season = call.argument("season", int)
    return generate_cache_key("retrosheet/rosters", {"season": season})


@cached(key=_rosters_cache_key)
async def rosters(season: int, context: BaseballContext | None = None) -> pl.DataFrame:
    """Fetch Retrosheet roster (.ROS) files for a given season.

    Reads all .ROS files for the season and returns a combined DataFrame.
    Edge Cases: Returns an empty DataFrame with the correct schema if no roster
    files are available or all fetch attempts return no data.
    """
    ctx = context or default_context()
    files = await _get_season_contents(season, ctx)
    ros_files = [f for f in files if f.endswith(".ROS")]
    if not ros_files:
        raise ServerError(f"Rosters not available for {season}")

    async def _fetch_one_roster(filename: str) -> pl.DataFrame | None:
        team = filename[:3]
        url = RETROSHEET_ROSTER_URL.format(season, team, season)
        raw_bytes = await ctx.http.get_text(url)
        if not raw_bytes:
            return None
        return parse_roster_csv(raw_bytes)

    tasks = [_fetch_one_roster(f) for f in ros_files]
    dfs = await asyncio.gather(*tasks)
    valid_dfs = [df for df in dfs if df is not None and df.height > 0]
    if not valid_dfs:
        return empty_rosters_frame()

    return pl.concat(valid_dfs)


def _park_codes_cache_key(_call: CacheCallArgs) -> str:
    return generate_cache_key("retrosheet/park_codes", {})


@cached(key=_park_codes_cache_key)
async def park_codes(context: BaseballContext | None = None) -> pl.DataFrame:
    """Fetch Retrosheet park code reference data.

    Edge Cases: Returns an empty DataFrame if the upstream file is unavailable.
    Column names are mapped from the raw CSV header to canonical PARK_CODE_COLUMNS.
    """
    ctx = context or default_context()
    raw_bytes = await ctx.http.get_text(RETROSHEET_PARKID_URL)
    if not raw_bytes:
        return pl.DataFrame()
    return parse_park_codes_csv(raw_bytes)


def _schedules_cache_key(call: CacheCallArgs) -> str:
    season = call.argument("season", int)
    return generate_cache_key("retrosheet/schedules", {"season": season})


@cached(key=_schedules_cache_key)
async def schedules(season: int, context: BaseballContext | None = None) -> pl.DataFrame:
    """Fetch Retrosheet schedule CSV for a given season.

    Edge Cases: Raises ServerError if the schedule file is not found in the
    season directory; returns an empty DataFrame if the fetch returns no data.
    """
    ctx = context or default_context()
    files = await _get_season_contents(season, ctx)
    file_name = f"{season}schedule.csv"
    if file_name not in files:
        raise ServerError(f"Schedule not available for {season}")

    url = RETROSHEET_SCHEDULE_URL.format(season, season)
    raw_bytes = await ctx.http.get_text(url)
    if not raw_bytes:
        return pl.DataFrame()
    return parse_schedule_csv(raw_bytes)


def _season_game_logs_cache_key(call: CacheCallArgs) -> str:
    season = call.argument("season", int)
    return generate_cache_key("retrosheet/season_game_logs", {"season": season})


@cached(key=_season_game_logs_cache_key)
async def season_game_logs(season: int, context: BaseballContext | None = None) -> pl.DataFrame:
    """Fetch Retrosheet season game logs (GL{season}.TXT) for a given season.

    Edge Cases: Raises ServerError if the game log file is not found; returns
    an empty DataFrame if the fetch returns no data.
    """
    ctx = context or default_context()
    files = await _get_season_contents(season, ctx)
    gamelog_file_name = f"GL{season}.TXT"
    if gamelog_file_name not in files:
        raise ServerError(f"Season game logs not available for {season}")

    url = RETROSHEET_SEASON_GAMELOG_URL.format(season, season)
    raw_bytes = await ctx.http.get_text(url)
    if not raw_bytes:
        return pl.DataFrame()
    return parse_gamelog_csv(raw_bytes)


def _gamelog_cache_key(call: CacheCallArgs) -> str:
    suffix = call.argument("suffix", str)
    return generate_cache_key(f"retrosheet/gamelog/{suffix}", {})


@cached(key=_gamelog_cache_key)
async def _get_gamelog_generic(suffix: str, context: BaseballContext | None = None) -> pl.DataFrame:
    ctx = context or default_context()
    url = RETROSHEET_GAMELOG_URL.format(suffix)
    raw_bytes = await ctx.http.get_text(url)
    if not raw_bytes:
        return pl.DataFrame()
    return parse_gamelog_csv(raw_bytes)


async def world_series_logs(context: BaseballContext | None = None) -> pl.DataFrame:
    """Fetch Retrosheet World Series game logs."""
    return await _get_gamelog_generic("WS", context=context)


async def all_star_game_logs(context: BaseballContext | None = None) -> pl.DataFrame:
    """Fetch Retrosheet All-Star Game logs."""
    return await _get_gamelog_generic("AS", context=context)


async def wild_card_logs(context: BaseballContext | None = None) -> pl.DataFrame:
    """Fetch Retrosheet Wild Card game logs."""
    return await _get_gamelog_generic("WC", context=context)


async def division_series_logs(context: BaseballContext | None = None) -> pl.DataFrame:
    """Fetch Retrosheet Division Series game logs."""
    return await _get_gamelog_generic("DV", context=context)


async def lcs_logs(context: BaseballContext | None = None) -> pl.DataFrame:
    """Fetch Retrosheet League Championship Series game logs."""
    return await _get_gamelog_generic("LC", context=context)
