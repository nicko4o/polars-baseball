from polars_baseball._schemas.mlb import (
    MLB_PEOPLE_REQUIRED,
    MLB_SCHEDULE_REQUIRED,
)


def test_mlb_required_columns_are_immutable() -> None:
    assert isinstance(MLB_PEOPLE_REQUIRED, tuple)
    assert isinstance(MLB_SCHEDULE_REQUIRED, tuple)
