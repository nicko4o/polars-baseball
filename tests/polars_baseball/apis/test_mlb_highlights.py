import json
from unittest.mock import AsyncMock

import polars as pl
import pytest

from polars_baseball._client import HttpClient
from polars_baseball.apis.mlb import mlb_game_highlights
from polars_baseball.context import BaseballContext
from polars_baseball.exceptions import InvalidParameterError

_MOCK_GAME_CONTENT_JSON = {
    "highlights": {
        "highlights": {
            "items": [
                {
                    "id": "789101",
                    "headline": "Judge hits solo homer",
                    "blurb": "Aaron Judge crushes a solo home run.",
                    "date": "2026-06-01T20:15:00Z",
                    "duration": "00:00:35",
                    "playId": "play-uuid-001",
                    "keywordsAll": [
                        {"type": "player_id", "value": "592450"},
                    ],
                    "playbacks": [
                        {"name": "mp4Avc", "url": "https://cuts.mlb.com/450k.mp4"},
                        {"name": "mp4Avc", "url": "https://cuts.mlb.com/2500k.mp4"},
                        {"name": "mp4Avc", "url": "https://cuts.mlb.com/1200k.mp4"},
                    ],
                },
                {
                    "id": "789102",
                    "headline": "Cole strikes out 10",
                    "blurb": "Gerrit Cole records 10th strikeout of the game.",
                    "date": "2026-06-01T21:30:00Z",
                    "duration": "00:00:45",
                    "playId": None,
                    "playbacks": [
                        {"name": "mp4Avc", "url": "https://cuts.mlb.com/cole_1800k.mp4"},
                    ],
                },
            ]
        }
    }
}

_MOCK_KEYWORD_EXTRACTION_JSON = {
    "highlights": {
        "highlights": {
            "items": [
                {
                    "mediaPlaybackId": "media-999",
                    "headline": "Ohtani RBI double",
                    "blurb": "Shohei Ohtani doubles.",
                    "date": "2026-08-10T22:00:00Z",
                    "duration": "00:00:20",
                    "keywordsAll": [
                        {"type": "player_id", "value": "660271"},
                        {"type": "play_id", "value": "kw-play-uuid-999"},
                    ],
                    "playbacks": [
                        {"name": "mp4Avc", "url": "https://cuts.mlb.com/ohtani_2500k.mp4"},
                    ],
                }
            ]
        }
    }
}

_MOCK_EMPTY_CONTENT_JSON: dict[str, object] = {"highlights": {"highlights": {"items": []}}}


@pytest.mark.asyncio
async def test_mlb_game_highlights_success() -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=json.dumps(_MOCK_GAME_CONTENT_JSON))
    context = BaseballContext(http=mock_http)

    df = await mlb_game_highlights(715789, context=context)

    assert isinstance(df, pl.DataFrame)
    assert df.height == 2
    assert df.columns == [
        "gamePk",
        "highlightId",
        "playId",
        "playerId",
        "title",
        "blurb",
        "duration",
        "date",
        "url",
        "best_mp4_url",
    ]

    # Verify highest bitrate url selection (2500k vs 450k/1200k)
    row_0 = df.to_dicts()[0]
    assert row_0["gamePk"] == 715789
    assert row_0["highlightId"] == "789101"
    assert row_0["playId"] == "play-uuid-001"
    assert row_0["playerId"] == 592450
    assert row_0["title"] == "Judge hits solo homer"
    assert row_0["blurb"] == "Aaron Judge crushes a solo home run."
    assert row_0["duration"] == "00:00:35"
    assert row_0["url"] == "https://cuts.mlb.com/2500k.mp4"
    assert row_0["best_mp4_url"] == "https://cuts.mlb.com/2500k.mp4"

    row_1 = df.to_dicts()[1]
    assert row_1["highlightId"] == "789102"
    assert row_1["playId"] is None
    assert row_1["playerId"] is None
    assert row_1["url"] == "https://cuts.mlb.com/cole_1800k.mp4"
    assert row_1["best_mp4_url"] == "https://cuts.mlb.com/cole_1800k.mp4"


@pytest.mark.asyncio
async def test_mlb_game_highlights_keyword_extraction() -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=json.dumps(_MOCK_KEYWORD_EXTRACTION_JSON))
    context = BaseballContext(http=mock_http)

    df = await mlb_game_highlights(823918, context=context)

    assert isinstance(df, pl.DataFrame)
    assert df.height == 1
    row = df.to_dicts()[0]
    assert row["gamePk"] == 823918
    assert row["highlightId"] == "media-999"
    assert row["playId"] == "kw-play-uuid-999"
    assert row["playerId"] == 660271
    assert row["title"] == "Ohtani RBI double"
    assert row["url"] == "https://cuts.mlb.com/ohtani_2500k.mp4"
    assert row["best_mp4_url"] == "https://cuts.mlb.com/ohtani_2500k.mp4"


@pytest.mark.asyncio
async def test_mlb_game_highlights_empty() -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=json.dumps(_MOCK_EMPTY_CONTENT_JSON))
    context = BaseballContext(http=mock_http)

    df = await mlb_game_highlights(715789, context=context)

    assert isinstance(df, pl.DataFrame)
    assert df.height == 0
    assert df.columns == [
        "gamePk",
        "highlightId",
        "playId",
        "playerId",
        "title",
        "blurb",
        "duration",
        "date",
        "url",
        "best_mp4_url",
    ]


@pytest.mark.asyncio
async def test_mlb_game_highlights_invalid_game_pk() -> None:
    with pytest.raises(InvalidParameterError, match="game_pk must be a positive integer"):
        await mlb_game_highlights(0)
