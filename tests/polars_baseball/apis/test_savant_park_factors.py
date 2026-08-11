from pathlib import Path
from unittest.mock import AsyncMock

import polars as pl
import pytest

from polars_baseball._client import HttpClient
from polars_baseball.apis.savant_leaderboards import savant_park_factors
from polars_baseball.context import BaseballContext
from polars_baseball.exceptions import InvalidParameterError

MOCK_PARK_FACTORS_HTML_2024 = """
<!DOCTYPE html>
<html>
<head><title>Statcast Park Factors</title></head>
<body>
<script>
    var data = [
        {
            "grouping_venue_conditions": "All",
            "key_is_year_rolling": "1",
            "key_num_years_rolling": "3",
            "key_year": "2024",
            "key_bat_side": "All",
            "venue_id": "15",
            "venue_name": "Chase Field",
            "main_team_id": "109",
            "name_display_club": "D-backs",
            "n_pa": "57490",
            "index_runs": "102",
            "index_hardhit": "101",
            "index_woba": "101",
            "index_wobatto": "99",
            "index_wobacon": "100",
            "index_xwobacon": "99",
            "index_xbacon": "100",
            "index_obp": "102",
            "index_so": "94",
            "index_bb": "99",
            "index_bacon": "101",
            "index_hits": "104",
            "index_1b": "104",
            "index_2b": "113",
            "index_3b": "168",
            "index_hr": "86",
            "year_range": "2022-2024"
        },
        {
            "grouping_venue_conditions": "All",
            "key_is_year_rolling": "1",
            "key_num_years_rolling": "3",
            "key_year": "2024",
            "key_bat_side": "All",
            "venue_id": "680",
            "venue_name": "T-Mobile Park",
            "main_team_id": "136",
            "name_display_club": "Mariners",
            "n_pa": "49700",
            "index_runs": "83",
            "index_hardhit": "98",
            "index_woba": "91",
            "index_wobatto": "96",
            "index_wobacon": "95",
            "index_xwobacon": "100",
            "index_xbacon": "100",
            "index_obp": "92",
            "index_so": "117",
            "index_bb": "95",
            "index_bacon": "94",
            "index_hits": "90",
            "index_1b": "90",
            "index_2b": "87",
            "index_3b": "35",
            "index_hr": "98",
            "year_range": "2022-2024"
        }
    ];
</script>
</body>
</html>
"""

MOCK_PARK_FACTORS_HTML_2023 = MOCK_PARK_FACTORS_HTML_2024.replace('"2024"', '"2023"').replace(
    '"2022-2024"', '"2021-2023"'
)


@pytest.mark.asyncio
async def test_savant_park_factors_single_year(tmp_path: Path) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=MOCK_PARK_FACTORS_HTML_2024)
    ctx = BaseballContext.with_file_cache(tmp_path, http=mock_http)

    df = await savant_park_factors(year=2024, context=ctx)
    assert isinstance(df, pl.DataFrame)
    assert df.height == 2
    assert "venue_id" in df.columns
    assert "park_factor" in df.columns
    assert "hr_factor" in df.columns
    assert df["venue_id"].to_list() == [15, 680]
    assert df["park_factor"].to_list() == [101, 91]
    assert df["hr_factor"].to_list() == [86, 98]


@pytest.mark.asyncio
async def test_savant_park_factors_year_range_tuple(tmp_path: Path) -> None:
    async def mock_get_text(url: str, params: dict[str, str] | None = None) -> str:
        if params and params.get("year") == "2023":
            return MOCK_PARK_FACTORS_HTML_2023
        return MOCK_PARK_FACTORS_HTML_2024

    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(side_effect=mock_get_text)
    ctx = BaseballContext.with_file_cache(tmp_path, http=mock_http)

    df = await savant_park_factors(year=(2023, 2024), context=ctx)
    assert isinstance(df, pl.DataFrame)
    assert df.height == 4
    assert set(df["year"].to_list()) == {2023, 2024}


@pytest.mark.asyncio
async def test_savant_park_factors_start_end_year(tmp_path: Path) -> None:
    async def mock_get_text(url: str, params: dict[str, str] | None = None) -> str:
        if params and params.get("year") == "2023":
            return MOCK_PARK_FACTORS_HTML_2023
        return MOCK_PARK_FACTORS_HTML_2024

    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(side_effect=mock_get_text)
    ctx = BaseballContext.with_file_cache(tmp_path, http=mock_http)

    df = await savant_park_factors(start_year=2023, end_year=2024, context=ctx)
    assert isinstance(df, pl.DataFrame)
    assert df.height == 4


@pytest.mark.asyncio
async def test_savant_park_factors_venue_filtering(tmp_path: Path) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=MOCK_PARK_FACTORS_HTML_2024)
    ctx = BaseballContext.with_file_cache(tmp_path, http=mock_http)

    df = await savant_park_factors(year=2024, venue_id=15, context=ctx)
    assert df.height == 1
    assert df["venue_id"][0] == 15


@pytest.mark.asyncio
async def test_savant_park_factors_invalid_params() -> None:
    with pytest.raises(InvalidParameterError):
        await savant_park_factors(bat_side="INVALID")  # type: ignore[arg-type]

    with pytest.raises(InvalidParameterError):
        await savant_park_factors(start_year=2024, end_year=2020)

    with pytest.raises(InvalidParameterError):
        await savant_park_factors(year=(2024, 2020))

    with pytest.raises(InvalidParameterError):
        await savant_park_factors(year=("2023", "2024"))  # type: ignore[arg-type]

    with pytest.raises(InvalidParameterError):
        await savant_park_factors(start_year="2023", end_year="2024")  # type: ignore[arg-type]

    with pytest.raises(InvalidParameterError):
        await savant_park_factors(year=2010)


@pytest.mark.asyncio
async def test_savant_park_factors_empty_response(tmp_path: Path) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value="<html><body><script>var data = [];</script></body></html>")
    ctx = BaseballContext.with_file_cache(tmp_path, http=mock_http)

    df = await savant_park_factors(year=2024, context=ctx)
    assert isinstance(df, pl.DataFrame)
    assert df.is_empty()


@pytest.mark.asyncio
async def test_savant_park_factors_year_list(tmp_path: Path) -> None:
    async def mock_get_text(url: str, params: dict[str, str] | None = None) -> str:
        if params and params.get("year") == "2023":
            return MOCK_PARK_FACTORS_HTML_2023
        return MOCK_PARK_FACTORS_HTML_2024

    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(side_effect=mock_get_text)
    ctx = BaseballContext.with_file_cache(tmp_path, http=mock_http)

    df = await savant_park_factors(year=[2023, 2024], context=ctx)
    assert isinstance(df, pl.DataFrame)
    assert df.height == 4
    assert set(df["year"].to_list()) == {2023, 2024}


@pytest.mark.asyncio
async def test_savant_park_factors_bat_side_r(tmp_path: Path) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=MOCK_PARK_FACTORS_HTML_2024)
    ctx = BaseballContext.with_file_cache(tmp_path, http=mock_http)

    df = await savant_park_factors(year=2024, bat_side="R", context=ctx)
    assert isinstance(df, pl.DataFrame)
    mock_http.get_text.assert_called_once()
    _, kwargs = mock_http.get_text.call_args
    assert kwargs.get("params", {}).get("batSide") == "R"
