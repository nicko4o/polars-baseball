"""Live contract tests for FanGraphs enum column codes."""

import typing

import polars as pl
import pytest

from polars_baseball._validation import validate_critical_columns_present
from polars_baseball.apis.fangraphs import FanGraphsRequest
from polars_baseball.enums.fangraphs import (
    FangraphsBattingStats,
    FangraphsFieldingStats,
    FangraphsPitchingStats,
    FangraphsStatsBase,
)
from polars_baseball.exceptions import InvalidSchemaError
from tests._async_utils import run_async


class TestCriticalColumnsValidator:
    """Tests for the validate_critical_columns_present helper (no live data)."""

    def test_validate_critical_present_passes(self) -> None:
        df = pl.DataFrame({"Name": ["A"], "Team": ["B"], "Season": [2024], "WAR": [1.0]})
        validate_critical_columns_present(df, {"Name", "Team", "Season", "WAR"})

    def test_validate_critical_present_raises(self) -> None:
        df = pl.DataFrame({"Name": ["A"], "WAR": [1.0]})
        with pytest.raises(InvalidSchemaError, match="Missing critical columns"):
            validate_critical_columns_present(df, {"Name", "Team", "WAR"})


@pytest.mark.live
class TestLiveFetchAndValidate:
    """Live tests that fetch real FanGraphs data and validate critical columns."""

    BATTING_CRITICAL = {"Name", "Team", "Season", "WAR", "OPS", "AVG"}
    PITCHING_CRITICAL = {"Name", "Team", "Season", "WAR", "ERA", "WHIP"}
    FIELDING_CRITICAL = {"Name", "Team", "Season", "Inn", "DRS", "UZR"}

    def _fetch_and_check(
        self, builder: typing.Callable[..., FanGraphsRequest], critical: set[str], **kwargs: int
    ) -> pl.DataFrame:
        from polars_baseball import BaseballContext, fg_data

        request = builder(**kwargs)

        async def run() -> pl.DataFrame:
            async with BaseballContext() as ctx:
                return await fg_data(request, context=ctx)

        df = run_async(run())
        missing = critical - set(df.columns)
        assert not missing, f"Missing critical columns: {missing}"
        return df

    def test_live_batting(self) -> None:
        from polars_baseball import FanGraphsRequest

        df = self._fetch_and_check(FanGraphsRequest.batting, self.BATTING_CRITICAL, start_season=2024)
        assert df.height > 0

    def test_live_pitching(self) -> None:
        from polars_baseball import FanGraphsRequest

        df = self._fetch_and_check(FanGraphsRequest.pitching, self.PITCHING_CRITICAL, start_season=2024)
        assert df.height > 0

    def test_live_fielding(self) -> None:
        from polars_baseball import FanGraphsRequest

        df = self._fetch_and_check(FanGraphsRequest.fielding, self.FIELDING_CRITICAL, start_season=2024)
        assert df.height > 0


@pytest.mark.live
class TestLiveCodeToNameMapping:
    """Verify that known stat codes produce expected column names in real FanGraphs responses."""

    BATTING_EXPECTATIONS: dict[str, str] = {
        "58": "WAR",
        "39": "OPS",
        "23": "AVG",
        "37": "OBP",
        "50": "wOBA",
        "61": "wRC+",
        "11": "HR",
    }

    PITCHING_EXPECTATIONS: dict[str, str] = {
        "59": "WAR",
        "6": "ERA",
        "45": "FIP",
        "42": "WHIP",
        "36": "K/9",
        "46": "GB/FB",
    }

    FIELDING_EXPECTATIONS: dict[str, str] = {
        "43": "Defense",
        "39": "UZR",
        "28": "DRS",
        "60": "OAA",
        "59": "CFraming",
    }

    @staticmethod
    def _fetch_and_check(
        codes: dict[str, str], builder: typing.Callable[..., FanGraphsRequest], enum_class: type[FangraphsStatsBase]
    ) -> None:
        from polars_baseball import BaseballContext, fg_data

        request = builder(start_season=2024, stat_columns=[enum_class.parse(c) for c in codes])

        async def run() -> pl.DataFrame:
            async with BaseballContext() as ctx:
                return await fg_data(request, context=ctx)

        df = run_async(run())
        for expected_name in codes.values():
            assert expected_name in df.columns, f"Missing column: {expected_name}"

    def test_batting_codes(self) -> None:
        from polars_baseball import FanGraphsRequest

        self._fetch_and_check(self.BATTING_EXPECTATIONS, FanGraphsRequest.batting, FangraphsBattingStats)

    def test_pitching_codes(self) -> None:
        from polars_baseball import FanGraphsRequest

        self._fetch_and_check(self.PITCHING_EXPECTATIONS, FanGraphsRequest.pitching, FangraphsPitchingStats)

    def test_fielding_codes(self) -> None:
        from polars_baseball import FanGraphsRequest

        self._fetch_and_check(self.FIELDING_EXPECTATIONS, FanGraphsRequest.fielding, FangraphsFieldingStats)


class TestEnumColumnDriftDetector:
    """Unit tests that detect if the enum column definitions drift from known values."""

    def test_batting_enum_all_unique_values(self) -> None:
        values = [m.value for m in FangraphsBattingStats]
        assert len(values) == len(set(values)), "Duplicate values in FangraphsBattingStats"

    def test_pitching_enum_all_unique_values(self) -> None:
        values = [m.value for m in FangraphsPitchingStats]
        assert len(values) == len(set(values)), "Duplicate values in FangraphsPitchingStats"

    def test_fielding_enum_all_unique_values(self) -> None:
        values = [m.value for m in FangraphsFieldingStats]
        assert len(values) == len(set(values)), "Duplicate values in FangraphsFieldingStats"

    def test_batting_all_includes_war(self) -> None:
        assert FangraphsBattingStats.WAR in FangraphsBattingStats.ALL()

    def test_pitching_all_includes_war(self) -> None:
        assert FangraphsPitchingStats.WAR in FangraphsPitchingStats.ALL()

    def test_fielding_all_includes_def(self) -> None:
        assert FangraphsFieldingStats.DEF in FangraphsFieldingStats.ALL()

    def test_batting_known_codes_parse_successfully(self) -> None:
        for code in ["58", "39", "23", "37", "50", "61", "11"]:
            member = FangraphsBattingStats.parse(code)
            assert member is not None

    def test_pitching_known_codes_parse_successfully(self) -> None:
        for code in ["59", "6", "45", "42", "36", "46"]:
            member = FangraphsPitchingStats.parse(code)
            assert member is not None

    def test_fielding_known_codes_parse_successfully(self) -> None:
        for code in ["43", "39", "28", "60", "59"]:
            member = FangraphsFieldingStats.parse(code)
            assert member is not None
