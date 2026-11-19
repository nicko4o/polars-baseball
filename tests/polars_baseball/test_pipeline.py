import html
import json

import polars as pl
import pytest

from polars_baseball.exceptions import UpstreamParseError
from polars_baseball.parsers.pipeline import MLBPipelineParser

_MOCK_VALID_JSON = {
    "payload": {
        "ROOT_QUERY": {
            "__typename": "Query",
            'getPlayerRankingsFromSelection({"limit":100,"slug":"sel-pr-2026-top100"})': [
                {
                    "rank": 1,
                    "playerEntity": {
                        "__typename": "PlayerEntity",
                        "eta": "2026",
                        "player": {"__ref": "Person:815908"},
                        "position": "SS",
                        "prospectBio": [
                            {
                                "__typename": "ProspectBio",
                                "contentText": "<p><strong>Scouting grades:</strong> Hit: 60 | Power: 60 | Run: 60 | Arm: 60 | Field: 55 | Overall: 65</p>",
                                "contentTitle": "2026",
                            }
                        ],
                        "signed": "Jan. 15, 2024 - MIL",
                    },
                }
            ],
        },
        "Person:815908": {
            "__typename": "Person",
            "batSideCode": "S",
            "birthCity": "San Cristobal",
            "birthCountry": "Dominican Republic",
            "birthDate": "2007-05-08",
            "currentAge": 19,
            "activeRoster": {"__ref": "Team:5015"},
            "height": "6' 1\"",
            "id": 815908,
            "pitchHandCode": "R",
            "useLastName": "Made",
            "useName": "Jesús",
            "weight": 221,
        },
        "Team:5015": {
            "__typename": "Team",
            "id": 5015,
            "name": "Biloxi Shuckers",
            "parentOrgName": "Milwaukee Brewers",
            "sport": {"__ref": "Sport:12"},
        },
        "Sport:12": {"__typename": "Sport", "abbreviation": "AA", "id": "12"},
    }
}

_MOCK_HTML_TEMPLATE = '<html><body><span data-init-state="{}"></span></body></html>'


def test_pipeline_parser_success() -> None:
    escaped_json = html.escape(json.dumps(_MOCK_VALID_JSON))
    html_content = _MOCK_HTML_TEMPLATE.format(escaped_json)

    parser = MLBPipelineParser()
    df = parser.parse(html_content)

    assert isinstance(df, pl.DataFrame)
    assert df.height == 1

    # Check resolved fields
    assert df["rank"][0] == 1
    assert df["player_id"][0] == 815908
    assert df["name"][0] == "Jesús Made"
    assert df["position"][0] == "SS"
    assert df["team"][0] == "Biloxi Shuckers"
    assert df["organization"][0] == "Milwaukee Brewers"
    assert df["level"][0] == "AA"
    assert df["age"][0] == 19
    assert df["height"][0] == "6' 1\""
    assert df["weight"][0] == 221
    assert df["bats"][0] == "S"
    assert df["throws"][0] == "R"
    assert df["eta"][0] == "2026"
    assert df["signed"][0] == "Jan. 15, 2024 - MIL"
    assert df["birth_date"][0] == "2007-05-08"
    assert df["birthplace"][0] == "San Cristobal, Dominican Republic"

    # Grades
    assert df["grade_overall"][0] == 65
    assert df["grade_hit"][0] == 60
    assert df["grade_power"][0] == 60
    assert df["grade_run"][0] == 60
    assert df["grade_arm"][0] == 60
    assert df["grade_field"][0] == 55
    assert df["grade_fastball"][0] is None


def test_pipeline_parser_no_span() -> None:
    parser = MLBPipelineParser()
    with pytest.raises(UpstreamParseError, match="No data-init-state"):
        parser.parse("<html><body>No state here</body></html>")


def test_pipeline_parser_empty_state() -> None:
    parser = MLBPipelineParser()
    with pytest.raises(UpstreamParseError, match="empty"):
        parser.parse('<html><body><span data-init-state=""></span></body></html>')


def test_pipeline_parser_invalid_json() -> None:
    parser = MLBPipelineParser()
    with pytest.raises(UpstreamParseError, match="JSON"):
        parser.parse('<html><body><span data-init-state="invalid-json"></span></body></html>')


def test_pipeline_parser_missing_rankings() -> None:
    invalid_state = {"payload": {"ROOT_QUERY": {"__typename": "Query"}}}
    escaped_json = html.escape(json.dumps(invalid_state))
    html_content = _MOCK_HTML_TEMPLATE.format(escaped_json)

    parser = MLBPipelineParser()
    with pytest.raises(UpstreamParseError, match="No player rankings data found"):
        parser.parse(html_content)


@pytest.mark.asyncio
@pytest.mark.parametrize("bad_list_type", ["../secret", "top100?x=1", "top100#frag", "a/b", ""])
async def test_prospect_rankings_rejects_unsafe_list_type(bad_list_type: str) -> None:
    from unittest.mock import AsyncMock

    from polars_baseball._client import HttpClient
    from polars_baseball.client import BaseballClient
    from polars_baseball.exceptions import InvalidParameterError

    mock_http = AsyncMock(spec=HttpClient)
    client = BaseballClient.with_null_cache(http=mock_http)
    with pytest.raises(InvalidParameterError):
        await client.mlb.prospect_rankings(list_type=bad_list_type)
    mock_http.get_text.assert_not_awaited()


def test_parse_scouting_grades_no_polynomial_redos() -> None:
    import time

    from polars_baseball.parsers.pipeline import _parse_scouting_grades

    adversarial = ("a " * 8000) + "Hit: 60 | Power: 55"
    start = time.monotonic()
    grades = _parse_scouting_grades(adversarial)
    elapsed = time.monotonic() - start

    assert grades == {"hit": 60, "power": 55}
    assert elapsed < 0.25
