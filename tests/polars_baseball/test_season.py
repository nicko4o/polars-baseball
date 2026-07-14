from datetime import date

import pytest

from polars_baseball._season import (
    most_recent_season,
    sanitize_date_range,
    statcast_date_range,
    validate_datestring,
)
from polars_baseball.exceptions import InvalidParameterError


def test_validate_datestring_valid() -> None:
    assert validate_datestring("2026-06-01") == date(2026, 6, 1)


def test_validate_datestring_invalid() -> None:
    with pytest.raises(InvalidParameterError, match="Incorrect data format"):
        validate_datestring("06-01-2026")


def test_validate_datestring_none() -> None:
    with pytest.raises(InvalidParameterError):
        validate_datestring(None)


def test_sanitize_date_range_warns_without_stdout(capsys: pytest.CaptureFixture[str]) -> None:
    with pytest.warns(UserWarning, match="No date range supplied"):
        sanitize_date_range(None, None)

    assert capsys.readouterr().out == ""


def test_most_recent_season_type() -> None:
    season = most_recent_season()
    assert isinstance(season, int)
    assert season >= 2024


def test_statcast_date_range_single_day() -> None:
    results = list(statcast_date_range(date(2024, 4, 1), date(2024, 4, 1), step=1, verbose=False))
    assert len(results) == 1
    assert results[0] == (date(2024, 4, 1), date(2024, 4, 1))


def test_statcast_date_range_multiple() -> None:
    results = list(statcast_date_range(date(2024, 4, 1), date(2024, 4, 5), step=3, verbose=False))
    assert len(results) == 2
    assert results[0] == (date(2024, 4, 1), date(2024, 4, 3))
    assert results[1] == (date(2024, 4, 4), date(2024, 4, 5))


def test_sanitize_date_range_swap() -> None:
    start, end = sanitize_date_range("2026-06-15", "2026-06-01")
    assert start == date(2026, 6, 1)
    assert end == date(2026, 6, 15)


def test_statcast_date_range_skips_offseason() -> None:
    results = list(statcast_date_range(date(2024, 11, 2), date(2025, 4, 1), step=5, verbose=False))
    assert len(results) > 0
    for low, high in results:
        assert low.month not in (12, 1)
        assert high.month not in (12, 1)


def test_load_valid_dates_failure_raises() -> None:
    from unittest.mock import patch

    from polars_baseball._season import _load_valid_dates

    with patch("polars_baseball._season.resources_files", side_effect=Exception("Failed to read resource")):
        with pytest.raises(Exception, match="Failed to read resource"):
            _load_valid_dates()


def test_validate_statcast_valid_dates_config_rejects_wrong_first_year() -> None:
    from polars_baseball._season import _validate_statcast_valid_dates_config

    with pytest.raises(RuntimeError, match="STATCAST_VALID_DATES minimum year"):
        _validate_statcast_valid_dates_config({2009: (date(2009, 1, 1), date(2009, 12, 31))})
