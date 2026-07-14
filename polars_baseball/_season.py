import json
import logging
import warnings
from collections.abc import Iterator
from datetime import date, datetime, timedelta
from importlib.resources import files as resources_files

from polars_baseball._config import SEASON_MID_MARCH_DAY, STATCAST_FIRST_YEAR
from polars_baseball.exceptions import InvalidParameterError

logger = logging.getLogger(__name__)

DATE_FORMAT = "%Y-%m-%d"


def _load_valid_dates() -> dict[int, tuple[date, date]]:
    json_path = resources_files("polars_baseball").joinpath("data", "statcast_valid_dates.json")
    data = json.loads(json_path.read_text(encoding="utf-8"))
    return {
        int(k): (
            datetime.strptime(v[0], DATE_FORMAT).date(),
            datetime.strptime(v[1], DATE_FORMAT).date(),
        )
        for k, v in data.items()
    }


STATCAST_VALID_DATES: dict[int, tuple[date, date]] = _load_valid_dates()


def _validate_statcast_valid_dates_config(valid_dates: dict[int, tuple[date, date]]) -> None:
    if not valid_dates:
        return
    if min(valid_dates) != STATCAST_FIRST_YEAR:
        raise RuntimeError("STATCAST_VALID_DATES minimum year must match STATCAST_FIRST_YEAR in config")


_validate_statcast_valid_dates_config(STATCAST_VALID_DATES)

_OFFSEASON_START_MONTH = 3
_OFFSEASON_END_MONTH = 11


def validate_datestring(date_text: str | None) -> date:
    if not date_text:
        raise InvalidParameterError("Incorrect data format, should be YYYY-MM-DD")
    try:
        return datetime.strptime(date_text, DATE_FORMAT).date()
    except ValueError as ex:
        raise InvalidParameterError("Incorrect data format, should be YYYY-MM-DD") from ex


def most_recent_season() -> int:
    today = date.today()
    if today.month > 3 or (today.month == 3 and today.day >= SEASON_MID_MARCH_DAY):
        return today.year
    return today.year - 1


def sanitize_date_range(start_dt: str | None, end_dt: str | None) -> tuple[date, date]:
    if start_dt is None and end_dt is None:
        today = date.today()
        start_dt = str(today - timedelta(1))
        end_dt = str(today)
        warnings.warn("No date range supplied, assuming yesterday's date.", stacklevel=2)

    if start_dt is None:
        start_dt = end_dt
    if end_dt is None:
        end_dt = start_dt

    start_dt_date = validate_datestring(start_dt)
    end_dt_date = validate_datestring(end_dt)

    if end_dt_date < start_dt_date:
        start_dt_date, end_dt_date = end_dt_date, start_dt_date

    return start_dt_date, end_dt_date


def statcast_date_range(start: date, stop: date, step: int, verbose: bool = True) -> Iterator[tuple[date, date]]:
    low = start

    while low <= stop:
        fallback = (
            low.replace(month=_OFFSEASON_START_MONTH, day=SEASON_MID_MARCH_DAY),
            low.replace(month=_OFFSEASON_END_MONTH, day=SEASON_MID_MARCH_DAY),
        )
        season_start, season_end = STATCAST_VALID_DATES.get(low.year, fallback)
        if low < season_start:
            low = season_start
            if verbose:
                warnings.warn("Skipping offseason dates.", stacklevel=2)
        elif low > season_end:
            next_year = low.year + 1
            next_fallback_start = date(
                month=_OFFSEASON_START_MONTH,
                day=SEASON_MID_MARCH_DAY,
                year=next_year,
            )
            low = STATCAST_VALID_DATES.get(
                next_year,
                (next_fallback_start, next_fallback_start),
            )[0]
            if verbose:
                warnings.warn("Skipping offseason dates.", stacklevel=2)

        if low > stop:
            return
        high = min(low + timedelta(step - 1), stop)
        yield low, high
        low += timedelta(days=step)
