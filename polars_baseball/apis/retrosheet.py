import polars as pl

from polars_baseball._cache import cached, generate_cache_key
from polars_baseball._concurrency import bounded_gather
from polars_baseball.context import BaseballContext
from polars_baseball.exceptions import (
    InvalidParameterError,
    ServerError,
)
from polars_baseball.gateways.retrosheet import RetrosheetGateway
from polars_baseball.parsers.retrosheet import (
    empty_rosters_frame,
    event_content_row,
    events_frame,
    parse_gamelog_csv,
    parse_park_codes_csv,
    parse_roster_csv,
    parse_schedule_csv,
)


async def events(
    season: int,
    game_type: str = "regular",
    context: BaseballContext | None = None,
    *,
    concurrency_limit: int = 5,
) -> pl.DataFrame:
    """Fetch Retrosheet event files for a given season.

    Returns one DataFrame with filename and raw event file content.
    Note: game_type parameter selects file extensions (".EVA"/".EVN" for "regular",
    post-season variants for "post", ".AS.EVE" for "asg"); raises InvalidParameterError
    for unknown types and ServerError if no event files are found.
    """
    ctx = context or BaseballContext.default()
    gateway = RetrosheetGateway(ctx)
    files = await gateway.get_season_contents(season)
    file_extension: tuple[str, ...]
    if game_type == "regular":
        file_extension = (".EVA", ".EVN")
    elif game_type == "post":
        file_extension = ("CS.EVE", "D1.EVE", "D2.EVE", "W1.EVE", "W2.EVE", "WS.EVE")
    elif game_type == "asg":
        file_extension = ("AS.EVE",)
    else:
        raise InvalidParameterError(
            f"Illegal type argument {game_type}, the valid types are: 'regular', 'post', and 'asg'."
        )

    season_events = [t for t in files if t.endswith(file_extension)]
    if not season_events:
        raise ServerError(f"Event files not available for {season}")

    async def _fetch_event(filename: str) -> dict[str, object]:
        raw = await gateway.get_event_file(season, filename)
        return event_content_row(season, game_type, filename, raw)

    tasks = [lambda f=f: _fetch_event(f) for f in season_events]
    results = await bounded_gather(tasks, concurrency_limit=concurrency_limit)
    rows = [row for row in results if row is not None]
    return events_frame(rows)


def _rosters_cache_key(**kw: object) -> str:
    season = kw.get("season")
    return generate_cache_key("retrosheet/rosters", {"season": season})


@cached(key=_rosters_cache_key)
async def rosters(
    season: int,
    context: BaseballContext | None = None,
    *,
    concurrency_limit: int = 5,
) -> pl.DataFrame:
    """Fetch Retrosheet roster (.ROS) files for a given season.

    Reads all .ROS files for the season and returns a combined DataFrame.
    Note: Returns an empty DataFrame with the correct schema if no roster
    files are available or all fetch attempts return no data.
    """
    ctx = context or BaseballContext.default()
    gateway = RetrosheetGateway(ctx)
    files = await gateway.get_season_contents(season)
    ros_files = [f for f in files if f.endswith(".ROS")]
    if not ros_files:
        raise ServerError(f"Rosters not available for {season}")

    async def _fetch_one_roster(filename: str) -> pl.DataFrame:
        team = filename[:3]
        raw_text = await gateway.get_roster_file(season, team)
        return parse_roster_csv(raw_text)

    tasks = [lambda f=f: _fetch_one_roster(f) for f in ros_files]
    dfs = await bounded_gather(tasks, concurrency_limit=concurrency_limit)
    valid_dfs = [df for df in dfs if df is not None and df.height > 0]
    if not valid_dfs:
        return empty_rosters_frame()

    return pl.concat(valid_dfs)


def _park_codes_cache_key(**_kw: object) -> str:
    return generate_cache_key("retrosheet/park_codes", {})


@cached(key=_park_codes_cache_key)
async def park_codes(context: BaseballContext | None = None) -> pl.DataFrame:
    """Fetch Retrosheet park code reference data.

    Column names are mapped from the raw CSV header to canonical PARK_CODE_COLUMNS.
    """
    ctx = context or BaseballContext.default()
    raw_text = await RetrosheetGateway(ctx).get_park_codes_csv()
    return parse_park_codes_csv(raw_text)


def _schedules_cache_key(**kw: object) -> str:
    season = kw.get("season")
    return generate_cache_key("retrosheet/schedules", {"season": season})


@cached(key=_schedules_cache_key)
async def schedules(season: int, context: BaseballContext | None = None) -> pl.DataFrame:
    """Fetch Retrosheet schedule CSV for a given season.

    Note: Raises ServerError if the schedule file is not found in the
    season directory.
    """
    ctx = context or BaseballContext.default()
    gateway = RetrosheetGateway(ctx)
    files = await gateway.get_season_contents(season)
    file_name = f"{season}schedule.csv"
    if file_name not in files:
        raise ServerError(f"Schedule not available for {season}")

    raw_text = await gateway.get_schedule_csv(season)
    return parse_schedule_csv(raw_text)


def _season_game_logs_cache_key(**kw: object) -> str:
    season = kw.get("season")
    return generate_cache_key("retrosheet/season_game_logs", {"season": season})


@cached(key=_season_game_logs_cache_key)
async def season_game_logs(season: int, context: BaseballContext | None = None) -> pl.DataFrame:
    """Fetch Retrosheet season game logs (GL{season}.TXT) for a given season.

    Note: Raises ServerError if the game log file is not found.
    """
    ctx = context or BaseballContext.default()
    gateway = RetrosheetGateway(ctx)
    files = await gateway.get_season_contents(season)
    gamelog_file_name = f"GL{season}.TXT"
    if gamelog_file_name not in files:
        raise ServerError(f"Season game logs not available for {season}")

    raw_text = await gateway.get_season_gamelog_csv(season)
    return parse_gamelog_csv(raw_text)


def _gamelog_cache_key(**kw: object) -> str:
    suffix = kw.get("suffix")
    return generate_cache_key(f"retrosheet/gamelog/{suffix}", {})


@cached(key=_gamelog_cache_key)
async def _get_gamelog_generic(suffix: str, context: BaseballContext | None = None) -> pl.DataFrame:
    ctx = context or BaseballContext.default()
    raw_text = await RetrosheetGateway(ctx).get_gamelog_csv(suffix)
    return parse_gamelog_csv(raw_text)


async def world_series_logs(context: BaseballContext | None = None) -> pl.DataFrame:
    """Fetch Retrosheet World Series game logs.

    Note:
        Delegates to _get_gamelog_generic with type code "WS".
        Returns empty DataFrame when season data is not available.
    """
    return await _get_gamelog_generic("WS", context=context)


async def all_star_game_logs(context: BaseballContext | None = None) -> pl.DataFrame:
    """Fetch Retrosheet All-Star Game logs.

    Note:
        Delegates to _get_gamelog_generic with type code "AS".
        Returns empty DataFrame when season data is not available.
    """
    return await _get_gamelog_generic("AS", context=context)


async def wild_card_logs(context: BaseballContext | None = None) -> pl.DataFrame:
    """Fetch Retrosheet Wild Card game logs.

    Note:
        Delegates to _get_gamelog_generic with type code "WC".
        Returns empty DataFrame when season data is not available.
    """
    return await _get_gamelog_generic("WC", context=context)


async def division_series_logs(context: BaseballContext | None = None) -> pl.DataFrame:
    """Fetch Retrosheet Division Series game logs.

    Note:
        Delegates to _get_gamelog_generic with type code "DV".
        Returns empty DataFrame when season data is not available.
    """
    return await _get_gamelog_generic("DV", context=context)


async def lcs_logs(context: BaseballContext | None = None) -> pl.DataFrame:
    """Fetch Retrosheet League Championship Series game logs.

    Note:
        Delegates to _get_gamelog_generic with type code "LC".
        Returns empty DataFrame when season data is not available.
    """
    return await _get_gamelog_generic("LC", context=context)
