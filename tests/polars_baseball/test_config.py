"""Tests for _config.py constants."""

from polars_baseball import _config


def test_statcast_date_step_defined() -> None:
    assert hasattr(_config, "STATCAST_DATE_STEP")
    assert isinstance(_config.STATCAST_DATE_STEP, int)
    assert _config.STATCAST_DATE_STEP > 0
