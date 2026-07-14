import asyncio
import logging
import warnings
from datetime import date
from typing import Literal

import polars as pl

from polars_baseball._config import OVERSIZE_DAYS_THRESHOLD, SAVANT_STATCAST_SEARCH_URL
from polars_baseball._season import sanitize_date_range, statcast_date_range
from polars_baseball.context import BaseballContext, default_context
from polars_baseball.exceptions import InvalidParameterError
from polars_baseball.gateways.savant import SavantGateway

logger = logging.getLogger(__name__)

_SC_SINGLE_GAME_REQUEST = f"{SAVANT_STATCAST_SEARCH_URL}?all=true&type=details&game_pk={{game_pk}}"
_BASE_SC_PARAMS: dict[str, str] = {
    "all": "true",
    "hfPT": "",
    "hfAB": "",
    "hfBBT": "",
    "hfPR": "",
    "hfZ": "",
    "stadium": "",
    "hfBBL": "",
    "hfNewZones": "",
    "hfGT": "R|PO|S|=",
    "hfSea": "",
    "hfSit": "",
    "hfOuts": "",
    "opponent": "",
    "pitcher_throws": "",
    "batter_stands": "",
    "hfSA": "",
    "position": "",
    "hfRO": "",
    "home_road": "",
    "hfFlag": "",
    "metric_1": "",
    "hfInn": "",
    "min_pitches": "0",
    "min_results": "0",
    "group_by": "name",
    "sort_col": "pitches",
    "player_event_sort": "h_launch_speed",
    "sort_order": "desc",
    "min_abs": "0",
    "type": "details",
}

# threshold imported from _config as OVERSIZE_DAYS_THRESHOLD

_OVERSIZE_WARNING = (
    "That's a nice request you got there. It'd be a shame if something were to happen to it. "
    "We strongly recommend that you enable caching before running this. "
    "Since the Statcast requests can take a *really* long time to run, if something were to happen, "
    "like: a disconnect; gremlins; computer repair by associates of Rudy Giuliani; "
    "electromagnetic interference from metal trash cans; etc.; "
    "you could lose a lot of progress. Enabling caching will allow you to immediately recover all the successful "
    "subqueries if that happens."
)

_SORT_COLS = ["game_date", "game_pk", "at_bat_number", "pitch_number"]


def _check_warning(start_dt: date, end_dt: date) -> None:
    if (end_dt - start_dt).days >= OVERSIZE_DAYS_THRESHOLD:
        warnings.warn(_OVERSIZE_WARNING, stacklevel=2)


async def _small_request(
    start_dt: date,
    end_dt: date,
    team: str | None = None,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    params: dict[str, str] = {
        **_BASE_SC_PARAMS,
        "player_type": "pitcher",
        "game_date_gt": str(start_dt),
        "game_date_lt": str(end_dt),
        "team": team if team else "",
    }
    ctx = context or default_context()
    return await SavantGateway(ctx).get_dataset(
        SAVANT_STATCAST_SEARCH_URL,
        params=params,
    )


async def _player_request(
    start_dt: date,
    end_dt: date,
    player_id: int,
    player_type: str,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    lookup_key = "batters_lookup[]" if player_type == "batter" else "pitchers_lookup[]"
    params: dict[str, str] = {
        **_BASE_SC_PARAMS,
        "player_type": player_type,
        "game_date_gt": str(start_dt),
        "game_date_lt": str(end_dt),
        lookup_key: str(player_id),
        "team": "",
    }
    ctx = context or default_context()
    return await SavantGateway(ctx).get_dataset(
        SAVANT_STATCAST_SEARCH_URL,
        params=params,
    )


async def statcast(
    start_dt: str | None = None,
    end_dt: str | None = None,
    team: str | None = None,
    verbose: bool = True,
    parallel: bool = True,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch Statcast pitch-level data for a date range.

    Dates beyond a single day are split into sub-queries internally (max 7 days per request)
    and concatenated.  Use ``team`` to filter for home games of a specific franchise.
    When ``parallel`` is true (default), sub-queries run concurrently.

    Edge Cases:
        - Returns empty DataFrame when no data matches the filters.
        - Emits a warning when the date range exceeds ~90 days (oversized threshold).
        - Requests spanning multiple calendar years are split at year boundaries.
    """
    start_dt_date, end_dt_date = sanitize_date_range(start_dt, end_dt)
    _check_warning(start_dt_date, end_dt_date)

    if verbose:
        logger.info("This is a large query, it may take a moment to complete")

    date_range = list(statcast_date_range(start_dt_date, end_dt_date, step=1, verbose=verbose))

    dataframe_list = []
    if parallel:
        if verbose and len(date_range) > 1:
            from tqdm.asyncio import tqdm as async_tqdm

            tasks = [_small_request(start, end, team, context=context) for start, end in date_range]
            dataframe_list = await async_tqdm.gather(*tasks)
        else:
            tasks = [_small_request(start, end, team, context=context) for start, end in date_range]
            dataframe_list = await asyncio.gather(*tasks)
    else:
        if verbose and len(date_range) > 1:
            from tqdm import tqdm

            for start, end in tqdm(date_range):
                dataframe_list.append(await _small_request(start, end, team, context=context))
        else:
            for start, end in date_range:
                dataframe_list.append(await _small_request(start, end, team, context=context))

    dfs = [df for df in dataframe_list if df is not None and not df.is_empty()]
    if not dfs:
        return pl.DataFrame()

    final_df = pl.concat(dfs, how="diagonal")
    return _sort_statcast(final_df)


async def statcast_single_game(game_pk: str | int, context: BaseballContext | None = None) -> pl.DataFrame:
    """Fetch Statcast data for a single game.

    Edge Cases:
        - Returns empty DataFrame when ``game_pk`` is invalid or the game has no data.
        - Postponed or cancelled games return an empty DataFrame.
    """
    url = _SC_SINGLE_GAME_REQUEST.format(game_pk=game_pk)
    ctx = context or default_context()
    df = await SavantGateway(ctx).get_dataset(url)
    if df.is_empty():
        return pl.DataFrame()

    return _sort_statcast(df)


def _check_player_id(player_id: int | None) -> int:
    if player_id is None:
        raise InvalidParameterError(
            "Player ID is required. If you need to find a player's id, try "
            "polars_baseball.playerid_lookup(last_name, first_name) and use their key_mlbam. "
            "If you want statcast data for all players, try the statcast() function."
        )
    return player_id


def _sort_statcast(df: pl.DataFrame) -> pl.DataFrame:
    existing = [c for c in _SORT_COLS if c in df.columns]
    if existing:
        return df.sort(existing, descending=True)
    return df


async def _statcast_player(
    player_type: Literal["batter", "pitcher"],
    start_dt: str | None,
    end_dt: str | None,
    player_id: int | None,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    pid = _check_player_id(player_id)
    start_dt_date, end_dt_date = sanitize_date_range(start_dt, end_dt)
    dfs = []
    curr = start_dt_date
    while curr <= end_dt_date:
        year_end = min(date(curr.year, 12, 31), end_dt_date)
        chunk = await _player_request(curr, year_end, pid, player_type, context=context)
        if not chunk.is_empty():
            dfs.append(chunk)
        curr = date(curr.year + 1, 1, 1)
    if not dfs:
        return pl.DataFrame()
    return _sort_statcast(pl.concat(dfs, how="diagonal"))


async def statcast_batter(
    start_dt: str | None = None,
    end_dt: str | None = None,
    player_id: int | None = None,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch Statcast data for a specific batter.

    Delegates to ``_statcast_player`` with ``player_type="batter"``.
    Requires a valid ``player_id`` (key_mlbam) or raises ``InvalidParameterError``.
    """
    return await _statcast_player("batter", start_dt, end_dt, player_id, context=context)


async def statcast_pitcher(
    start_dt: str | None = None,
    end_dt: str | None = None,
    player_id: int | None = None,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch Statcast data for a specific pitcher.

    Delegates to ``_statcast_player`` with ``player_type="pitcher"``.
    Requires a valid ``player_id`` (key_mlbam) or raises ``InvalidParameterError``.
    """
    return await _statcast_player("pitcher", start_dt, end_dt, player_id, context=context)
