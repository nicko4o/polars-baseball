import pytest

from polars_baseball.enums.fangraphs import (
    FangraphsBattingStats,
    FangraphsFieldingStats,
    FangraphsLeague,
    FangraphsPitchingStats,
    FangraphsStatsCategory,
    stat_list_from_str,
    stat_list_to_str,
)
from polars_baseball.exceptions import InvalidParameterError


def test_fangraphs_enum_parsing_case_insensitive() -> None:
    # Test EnumBase.parse case-insensitivity via FangraphsLeague
    assert FangraphsLeague.parse("al") == FangraphsLeague.AL
    assert FangraphsLeague.parse("AL") == FangraphsLeague.AL
    assert FangraphsLeague.parse("Al") == FangraphsLeague.AL


def test_fangraphs_enum_parsing_invalid() -> None:
    with pytest.raises(InvalidParameterError, match="Invalid value"):
        FangraphsLeague.parse("INVALID_LEAGUE")


def test_fangraphs_stats_all_uniqueness() -> None:
    # Verify that ALL() returns unique columns and contains expected core values
    batting_all = FangraphsBattingStats.ALL()
    assert len(batting_all) == len(set(batting_all))
    assert FangraphsBattingStats.WAR in batting_all

    pitching_all = FangraphsPitchingStats.ALL()
    assert len(pitching_all) == len(set(pitching_all))
    assert FangraphsPitchingStats.WAR in pitching_all

    fielding_all = FangraphsFieldingStats.ALL()
    assert len(fielding_all) == len(set(fielding_all))
    assert FangraphsFieldingStats.DEF in fielding_all


def test_stat_list_from_str_and_to_str() -> None:
    # Verify stat list parsing and formatting
    cols = stat_list_from_str(
        stat_category=FangraphsStatsCategory.BATTING,
        values=["WAR", "OPS"],
    )
    assert FangraphsBattingStats.WAR in cols
    assert FangraphsBattingStats.OPS in cols

    serialized = stat_list_to_str(cols)
    # Common columns are stripped/replaced with 'c'
    assert serialized.startswith("c,")
    assert "58" in serialized  # WAR value
    assert "39" in serialized  # OPS value
