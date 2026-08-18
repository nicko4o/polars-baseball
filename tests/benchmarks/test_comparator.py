from benchmarks.models import BaselineRecord
from benchmarks.tracking.comparator import check_regression


def _record(name: str, wall_time: float, **dimensions: object) -> BaselineRecord:
    base_dimensions: dict[str, object] = {"api": "lahman", "start_date": "all", "end_date": "all"}
    base_dimensions.update(dimensions)
    return {
        "name": name,
        "dimensions": base_dimensions,
        "metrics": {"wall_time_seconds": wall_time},
    }


def _baseline(*records: BaselineRecord) -> list[BaselineRecord]:
    return list(records)


def test_regression_detected_within_same_profile() -> None:
    history = _baseline(_record("lahman_batting", 1.0), _record("lahman_batting", 1.2))
    result = check_regression(2.0, history, profile_name="lahman_batting")
    assert result.is_regression is True


def test_no_regression_when_current_inline_with_history() -> None:
    history = _baseline(_record("lahman_batting", 1.0), _record("lahman_batting", 1.2))
    result = check_regression(1.1, history, profile_name="lahman_batting")
    assert result.is_regression is False


def test_lahman_profiles_do_not_contaminate_each_other() -> None:
    """Batting/pitching/people share identical dimensions; a batting regression.

    Regression to 0.030 is masked by the inflated cross-profile std when profiles are merged.
    """
    history = _baseline(
        _record("lahman_batting", 0.0217),
        _record("lahman_batting", 0.0230),
        _record("lahman_pitching", 0.0150),
        _record("lahman_people", 0.0129),
    )
    result = check_regression(0.030, history, profile_name="lahman_batting")
    assert result.is_regression is True


def test_dimensions_filter_excludes_other_apis() -> None:
    history = _baseline(
        _record("statcast_7day_warm", 0.0357, api="statcast"),
        _record("statcast_7day_warm", 0.0360, api="statcast"),
        _record("standings_2024", 0.008, api="standings"),
    )
    result = check_regression(0.07, history, dimensions={"api": "statcast"})
    assert result.is_regression is True


def test_fallback_to_dimensions_when_name_absent() -> None:
    history = _baseline(_record("lahman_batting", 1.0), _record("lahman_batting", 1.2))
    for record in history:
        record.pop("name")
    result = check_regression(2.0, history, dimensions={"api": "lahman"})
    assert result.is_regression is True


def test_insufficient_history_returns_no_regression() -> None:
    history = _baseline(_record("lahman_batting", 1.0))
    result = check_regression(5.0, history, profile_name="lahman_batting")
    assert result.is_regression is False
    assert result.baseline_mean == 5.0
