"""RED: Tests for _validation module — module does not exist yet."""

from typing import Any

import polars as pl
import pytest

from polars_baseball._validation import (
    validate_critical_columns_present,
    validate_next_data_structure,
)
from polars_baseball.exceptions import InvalidSchemaError, UpstreamStructureChangedError


def _valid_next_data() -> dict[str, Any]:
    return {
        "props": {
            "pageProps": {
                "dehydratedState": {
                    "queries": [
                        {
                            "queryKey": [
                                "leaders/major-league/data",
                                {"pos": "all", "stats": "bat"},
                            ],
                            "state": {
                                "data": {
                                    "data": [
                                        {
                                            "Name": "Mike Trout",
                                            "playerid": 19755,
                                            "WAR": 8.5,
                                        },
                                    ],
                                },
                            },
                        },
                    ],
                },
            },
        },
    }


class TestCriticalColumnsValidator:
    def test_valid_passes(self) -> None:
        df = pl.DataFrame({"Name": ["A"], "Team": ["B"], "Season": [2024], "WAR": [1.0]})
        validate_critical_columns_present(df, {"Name", "Team", "Season", "WAR"})

    def test_missing_columns_raises(self) -> None:
        df = pl.DataFrame({"Name": ["A"], "WAR": [1.0]})
        with pytest.raises(InvalidSchemaError, match="Missing critical columns"):
            validate_critical_columns_present(df, {"Name", "Team", "WAR"})


class TestValidateNextDataStructure:
    def test_valid_structure_returns_queries_list(self) -> None:
        data = _valid_next_data()
        result = validate_next_data_structure(data)
        assert isinstance(result, list)
        assert len(result) == 1
        assert "queryKey" in result[0]

    def test_non_dict_root_raises(self) -> None:
        with pytest.raises(UpstreamStructureChangedError):
            validate_next_data_structure("not a dict")

    def test_missing_props_raises(self) -> None:
        with pytest.raises(UpstreamStructureChangedError):
            validate_next_data_structure({"no_props": True})

    def test_missing_page_props_raises(self) -> None:
        with pytest.raises(UpstreamStructureChangedError):
            validate_next_data_structure({"props": {}})

    def test_missing_dehydrated_state_raises(self) -> None:
        with pytest.raises(UpstreamStructureChangedError):
            validate_next_data_structure({"props": {"pageProps": {}}})

    def test_queries_not_a_list_raises(self) -> None:
        with pytest.raises(UpstreamStructureChangedError):
            validate_next_data_structure(
                {
                    "props": {"pageProps": {"dehydratedState": {"queries": "not_a_list"}}},
                }
            )

    def test_error_contains_label_and_path(self) -> None:
        with pytest.raises(UpstreamStructureChangedError, match=r"pageProps"):
            validate_next_data_structure({"props": {}})

    def test_error_contains_actual_type(self) -> None:
        with pytest.raises(UpstreamStructureChangedError, match=r"got str"):
            validate_next_data_structure(
                {
                    "props": {"pageProps": {"dehydratedState": {"queries": "not_a_list"}}},
                }
            )

    def test_accepts_label(self) -> None:
        data = _valid_next_data()
        result = validate_next_data_structure(data, label="CUSTOM")
        assert isinstance(result, list)
        assert len(result) == 1
