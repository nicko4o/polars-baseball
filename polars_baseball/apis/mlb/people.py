import polars as pl

from polars_baseball._cache import cached
from polars_baseball.apis.mlb._contracts import (
    MLB_CACHE_MAX_AGE,
    people_awards_cache_key,
    people_awards_url,
    people_cache_key,
    people_url,
)
from polars_baseball.context import BaseballContext, default_context
from polars_baseball.exceptions import InvalidParameterError
from polars_baseball.gateways.mlb import MlbStatsGateway
from polars_baseball.parsers.mlb import parse_mlb_people, parse_mlb_people_awards


@cached(key=people_cache_key, max_age=MLB_CACHE_MAX_AGE)
async def _fetch_mlb_people(
    person_ids: list[int] | int,
    force_update: bool = False,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    ids_str = ",".join(map(str, person_ids)) if isinstance(person_ids, list) else str(person_ids)
    ctx = context or default_context()
    params = {"personIds": ids_str}
    return await MlbStatsGateway(ctx).fetch(
        people_url(), params, "Failed to fetch or parse MLB people data", parse_mlb_people
    )


@cached(key=people_awards_cache_key, max_age=MLB_CACHE_MAX_AGE)
async def _fetch_mlb_people_awards(
    person_id: int,
    force_update: bool = False,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    url = people_awards_url(person_id)
    ctx = context or default_context()
    return await MlbStatsGateway(ctx).fetch(
        url,
        None,
        "Failed to fetch or parse MLB people awards data",
        lambda d: parse_mlb_people_awards(d, person_id),
    )


async def mlb_people(
    person_ids: list[int] | int,
    force_update: bool = False,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch player biographical and career information from the MLB Stats API.

    Validates that all person_ids are positive integers. Returns an empty
    DataFrame when the API returns no matching people.

    Note:
        Raises InvalidParameterError if person_ids is empty or contains
        non-positive integers.
    """
    if not person_ids:
        raise InvalidParameterError("person_ids must not be empty.")

    if isinstance(person_ids, list):
        for pid in person_ids:
            if not isinstance(pid, int) or pid <= 0:
                raise InvalidParameterError(f"Invalid player ID: {pid}. Must be positive integer.")
    elif not isinstance(person_ids, int) or person_ids <= 0:
        raise InvalidParameterError(f"Invalid player ID: {person_ids}. Must be positive integer.")

    return await _fetch_mlb_people(
        person_ids=person_ids,
        force_update=force_update,
        context=context,
    )


async def mlb_people_awards(
    person_id: int,
    force_update: bool = False,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch official MLB award timeline rows for a single person.

    This endpoint is person-centric MLB Stats API data. It does not replace
    Lahman award tables or award vote-share tables.
    """
    if person_id <= 0:
        raise InvalidParameterError("person_id must be a positive integer.")

    return await _fetch_mlb_people_awards(
        person_id=person_id,
        force_update=force_update,
        context=context,
    )
