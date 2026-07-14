"""Tests for NEXT_DATA schema validation (imports from _validation.py)."""

import json
from typing import Any

import pytest

from polars_baseball._validation import validate_next_data_structure
from polars_baseball.exceptions import UpstreamStructureChangedError
from polars_baseball.parsers.fangraphs import FangraphsHTMLParser


def _valid_next_data() -> dict[str, Any]:
    return {
        "props": {
            "pageProps": {
                "dehydratedState": {
                    "queries": [
                        {
                            "queryKey": ["leaders/major-league/data", {"pos": "all", "stats": "bat"}],
                            "state": {
                                "data": {
                                    "data": [
                                        {"Name": "Mike Trout", "playerid": 19755, "WAR": 8.5},
                                    ],
                                },
                            },
                        },
                    ],
                },
            },
        },
    }


def _to_html(next_data: Any) -> str:
    return f'<html><script id="__NEXT_DATA__" type="application/json">{json.dumps(next_data)}</script></html>'


class TestValidateNextDataStandalone:
    """Tests for the standalone validate_next_data_structure function."""

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

    def test_error_message_contains_label_and_path(self) -> None:
        with pytest.raises(UpstreamStructureChangedError, match=r"pageProps"):
            validate_next_data_structure({"props": {}})

    def test_error_message_contains_actual_type(self) -> None:
        with pytest.raises(UpstreamStructureChangedError, match=r"got str"):
            validate_next_data_structure(
                {
                    "props": {"pageProps": {"dehydratedState": {"queries": "not_a_list"}}},
                }
            )

    def test_validator_accepts_label(self) -> None:
        data = _valid_next_data()
        result = validate_next_data_structure(data, label="CUSTOM")
        assert isinstance(result, list)
        assert len(result) == 1


class TestParserUsesValidator:
    """Verify parser calls the validator and preserves existing behavior."""

    def test_parser_parse_still_works(self) -> None:
        html = _to_html(_valid_next_data())
        df = FangraphsHTMLParser().parse(html)
        assert df.height == 1
        assert df["Name"][0] == "Mike Trout"

    def test_parser_rejects_bad_structure(self) -> None:
        html = _to_html("not_a_dict")
        with pytest.raises(UpstreamStructureChangedError):
            FangraphsHTMLParser().parse(html)
