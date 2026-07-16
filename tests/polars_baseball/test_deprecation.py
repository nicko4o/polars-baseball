import pytest

import polars_baseball as pb


def test_legacy_fg_aliases_warning_and_resolution() -> None:
    legacy_names = [
        "fg_batting",
        "fg_fielding",
        "fg_pitching",
        "fg_team_batting",
        "fg_team_fielding",
        "fg_team_pitching",
    ]

    for name in legacy_names:
        with pytest.warns(DeprecationWarning) as record:
            func = getattr(pb, name)

        # Verify warning message
        assert len(record) == 1
        assert "deprecated" in str(record[0].message)

        # Verify returned function resolves to the namespace version
        target_name = name.replace("fg_team_", "team_").replace("fg_", "")
        expected_func = getattr(pb.fangraphs, target_name)
        assert func is expected_func


def test_nonexistent_attribute_raises_attribute_error() -> None:
    with pytest.raises(AttributeError):
        _ = pb.nonexistent_func_123


def test_dir_contains_deprecated_aliases() -> None:
    dir_symbols = dir(pb)
    legacy_names = [
        "fg_batting",
        "fg_fielding",
        "fg_pitching",
        "fg_team_batting",
        "fg_team_fielding",
        "fg_team_pitching",
    ]
    for name in legacy_names:
        assert name in dir_symbols
