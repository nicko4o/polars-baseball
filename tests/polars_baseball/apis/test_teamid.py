from unittest.mock import MagicMock, patch

import polars as pl
import pytest

from polars_baseball.apis.teamid import team_ids


@pytest.fixture
def mock_team_data() -> pl.DataFrame:
    return pl.DataFrame(
        {
            "yearID": [2026, 2026, 2025],
            "lgID": ["AL", "NL", "AL"],
            "teamID": ["LAA", "LAD", "OAK"],
            "franchID": ["ANA", "LAD", "ATH"],
            "teamIDfg": [1, 2, 3],
            "teamIDBR": ["ANA", "LAD", "OAK"],
            "teamIDretro": ["ANA", "LAD", "OAK"],
        }
    )


@patch("polars_baseball.apis.teamid.pl.read_csv")
def test_team_ids(mock_read_csv: MagicMock, mock_team_data: pl.DataFrame) -> None:
    mock_read_csv.return_value = mock_team_data

    df_all = team_ids()
    assert df_all.height == 3

    df_2026 = team_ids(season=2026)
    assert df_2026.height == 2
    assert set(df_2026["yearID"].to_list()) == {2026}

    df_2026_al = team_ids(season=2026, league="AL")
    assert df_2026_al.height == 1
    assert df_2026_al["teamID"][0] == "LAA"
