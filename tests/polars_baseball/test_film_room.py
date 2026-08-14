import polars as pl
import pytest

from polars_baseball.apis.mlb.film_room import FilmRoomQueryBuilder, film_room_cache_key, film_room_search
from polars_baseball.exceptions import InvalidParameterError, UpstreamParseError
from polars_baseball.parsers.film_room import FILM_ROOM_SCHEMA, parse_film_room_search


def test_film_room_query_builder_default() -> None:
    q = FilmRoomQueryBuilder.build()
    assert q == 'ContentTags = ["home-run"] Order By Timestamp DESC'


def test_film_room_query_builder_filters() -> None:
    q = FilmRoomQueryBuilder.build(
        player_ids=[660271, 545361],
        team_ids=119,
        seasons=2024,
        date_range=("2024-04-01", "2024-10-01"),
        event_types=["Home Run", "Double"],
        pitch_types="FF",
        min_exit_velocity=100.0,
        max_exit_velocity=115.5,
        min_distance=400,
        max_distance=480,
    )
    assert "PlayerID = [660271, 545361]" in q
    assert "TeamID = [119]" in q
    assert "Season = [2024]" in q
    assert 'Date = ["2024-04-01", "2024-10-01"]' in q
    assert 'HitResult = ["Home Run", "Double"]' in q
    assert 'PitchType = ["FF"]' in q
    assert "ExitVelocity >= 100.0" in q
    assert "ExitVelocity <= 115.5" in q
    assert "HitDistance >= 400" in q
    assert "HitDistance <= 480" in q
    assert q.endswith("Order By Timestamp DESC")


def test_film_room_query_builder_escaping() -> None:
    q = FilmRoomQueryBuilder.build(event_types=['Home "Run"'])
    assert r'HitResult = ["Home \"Run\""]' in q


def test_film_room_query_builder_raw_override() -> None:
    raw = 'ContentTags = ["clutch-moment"]'
    q = FilmRoomQueryBuilder.build(query=raw)
    assert q == raw


def test_film_room_cache_key_hash() -> None:
    key1 = film_room_cache_key(player_ids=660271, limit=50)
    key2 = film_room_cache_key(player_ids=660271, limit=50)
    key3 = film_room_cache_key(player_ids=660271, limit=100)
    assert key1 == key2
    assert key1 != key3
    assert len(key1) == 32  # MD5 hex length


def test_parse_film_room_search_empty() -> None:
    df = parse_film_room_search({"data": {"search": {"plays": [], "total": 0}}})
    assert isinstance(df, pl.DataFrame)
    assert df.is_empty()
    assert set(df.columns) == set(FILM_ROOM_SCHEMA.keys())


def test_parse_film_room_search_invalid_type() -> None:
    with pytest.raises(UpstreamParseError):
        parse_film_room_search("invalid json")


def test_parse_film_room_search_valid_payload() -> None:
    mock_payload = {
        "data": {
            "search": {
                "total": 1,
                "plays": [
                    {
                        "id": "clip-12345",
                        "gameDate": "2024-05-15T00:00:00Z",
                        "title": "Shohei Ohtani's 450-foot home run",
                        "blurb": "Shohei Ohtani smashes a solo home run to deep center field.",
                        "fields": [
                            {"name": "playerid", "value": "660271"},
                            {"name": "playername", "value": "Shohei Ohtani"},
                            {"name": "eventtype", "value": "Home Run"},
                            {"name": "exitvelocity", "value": "112.4"},
                            {"name": "hitdistance", "value": "450"},
                        ],
                        "playbacks": [
                            {
                                "name": "mp4 1200K",
                                "url": "https://media.mlb.com/1200k.mp4",
                                "bitrate": 1200,
                                "width": 640,
                                "height": 360,
                            },
                            {
                                "name": "mp4 4000K",
                                "url": "https://media.mlb.com/4000k.mp4",
                                "bitrate": 4000,
                                "width": 1280,
                                "height": 720,
                            },
                            {
                                "name": "hlsStream",
                                "url": "https://media.mlb.com/stream.m3u8",
                                "bitrate": 0,
                                "width": 0,
                                "height": 0,
                            },
                        ],
                    }
                ],
            }
        }
    }

    df = parse_film_room_search(mock_payload)
    assert len(df) == 1
    row = df.to_dicts()[0]
    assert row["content_id"] == "clip-12345"
    assert str(row["date"]) == "2024-05-15"
    assert row["title"] == "Shohei Ohtani's 450-foot home run"
    assert row["player_id"] == 660271
    assert row["player_name"] == "Shohei Ohtani"
    assert row["event_type"] == "Home Run"
    assert row["exit_velocity"] == 112.4
    assert row["hit_distance"] == 450
    assert row["best_mp4_url"] == "https://media.mlb.com/4000k.mp4"
    assert row["hls_url"] == "https://media.mlb.com/stream.m3u8"
    assert len(row["playbacks"]) == 3


def test_parse_film_room_search_no_playbacks() -> None:
    mock_payload = {
        "data": {
            "search": {
                "total": 1,
                "plays": [
                    {
                        "id": "clip-999",
                        "gameDate": "2024-05-15",
                        "mediaPlayback": [
                            {
                                "title": "Great Catch",
                                "blurb": "Outfielder makes a diving catch",
                            }
                        ],
                    }
                ],
            }
        }
    }
    df = parse_film_room_search(mock_payload)
    assert len(df) == 1
    row = df.to_dicts()[0]
    assert row["content_id"] == "clip-999"
    assert row["best_mp4_url"] is None
    assert row["hls_url"] is None
    assert row["playbacks"] == []


@pytest.mark.asyncio
async def test_film_room_search_parameter_validation() -> None:
    with pytest.raises(InvalidParameterError, match="limit must be greater than 0"):
        await film_room_search(limit=0)

    with pytest.raises(InvalidParameterError, match="cannot be an empty sequence"):
        await film_room_search(player_ids=[])

    with pytest.raises(InvalidParameterError, match="cannot be an empty sequence"):
        await film_room_search(event_types=[])

    with pytest.raises(InvalidParameterError, match="date_range must be a tuple"):
        await film_room_search(date_range=("2024-01-01",))  # type: ignore[arg-type]

    with pytest.raises(InvalidParameterError, match="YYYY-MM-DD"):
        await film_room_search(date_range=("invalid", "2024-01-02"))

    with pytest.raises(InvalidParameterError, match="cannot be after end_date"):
        await film_room_search(date_range=("2024-05-01", "2024-04-01"))

    with pytest.raises(InvalidParameterError, match="min_exit_velocity .* cannot exceed"):
        await film_room_search(min_exit_velocity=115.0, max_exit_velocity=100.0)

    with pytest.raises(InvalidParameterError, match="min_distance .* cannot exceed"):
        await film_room_search(min_distance=450, max_distance=400)

    with pytest.raises(InvalidParameterError, match="cannot be an empty string"):
        await film_room_search(event_types="")

    with pytest.raises(InvalidParameterError, match="cannot be an empty string"):
        await film_room_search(pitch_types="   ")

    with pytest.raises(InvalidParameterError, match="cannot be an empty string"):
        await film_room_search(query="")


def test_parse_film_room_search_forge_cdn_fallback() -> None:
    mock_payload = {
        "data": {
            "search": {
                "total": 1,
                "plays": [
                    {
                        "id": "play-100",
                        "gameDate": "2024-08-13",
                        "mediaPlayback": [
                            {
                                "id": "mb-100",
                                "title": "Kerry Carpenter's two-run homer",
                                "blurb": "Kerry Carpenter hits a homer",
                                "date": "2024-08-13",
                                "mediaPlaybackId": "f7071359-b8485b07-ba6767c1-csvm-diamondx64-asset",
                            }
                        ],
                    }
                ],
            }
        }
    }
    df = parse_film_room_search(mock_payload)
    assert len(df) == 1
    row = df.to_dicts()[0]
    expected_url = (
        "https://mlb-cuts-diamond.mlb.com/FORGE/2024/2024-08/13/"
        "f7071359-b8485b07-ba6767c1-csvm-diamondx64-asset_1280x720_59_4000K.mp4"
    )
    assert row["best_mp4_url"] == expected_url
    assert len(row["playbacks"]) == 1
    assert row["playbacks"][0]["url"] == expected_url
    assert row["playbacks"][0]["bitrate"] == 4000


def test_film_room_query_builder_date_range_formats() -> None:
    from datetime import date, datetime

    # String ISO timestamps
    q1 = FilmRoomQueryBuilder.build(date_range=("2024-08-13T00:00:00Z", "2024-08-14T23:59:59Z"))
    assert 'Date = ["2024-08-13", "2024-08-14"]' in q1

    # Python date objects
    q2 = FilmRoomQueryBuilder.build(date_range=(date(2024, 8, 13), date(2024, 8, 14)))  # type: ignore[arg-type]
    assert 'Date = ["2024-08-13", "2024-08-14"]' in q2

    # Python datetime objects
    q3 = FilmRoomQueryBuilder.build(date_range=(datetime(2024, 8, 13, 10, 0), datetime(2024, 8, 14, 20, 0)))  # type: ignore[arg-type]
    assert 'Date = ["2024-08-13", "2024-08-14"]' in q3


@pytest.mark.asyncio
async def test_film_room_gateway_pagination_early_break() -> None:
    from unittest.mock import AsyncMock

    from polars_baseball._client import HttpClient
    from polars_baseball.context import BaseballContext
    from polars_baseball.gateways.film_room import FilmRoomGateway

    mock_http = AsyncMock(spec=HttpClient)

    page_1_data = {
        "data": {
            "search": {
                "total": 24,
                "plays": [
                    {
                        "id": f"play-{i}",
                        "gameDate": "2024-08-13",
                        "mediaPlayback": [{"title": f"Play {i}", "date": "2024-08-13"}],
                    }
                    for i in range(20)
                ],
            }
        }
    }
    page_2_data = {
        "data": {
            "search": {
                "total": 24,
                "plays": [
                    {
                        "id": f"play-{i}",
                        "gameDate": "2024-08-13",
                        "mediaPlayback": [{"title": f"Play {i}", "date": "2024-08-13"}],
                    }
                    for i in range(20, 24)
                ],
            }
        }
    }

    import json

    mock_http.post_json = AsyncMock(
        side_effect=[
            json.dumps(page_1_data),
            json.dumps(page_2_data),
        ]
    )
    ctx = BaseballContext(http=mock_http)
    gateway = FilmRoomGateway(ctx)

    # Request limit=100 (which would be 5 pages with PAGE_SIZE=20)
    df = await gateway.fetch_search("dummy_query", limit=100, error_msg="Error", parser=parse_film_room_search)

    # Because page 2 returned 4 items (< 20 fetch_limit), it must break early and make only 2 HTTP requests
    assert len(df) == 24
    assert mock_http.post_json.call_count == 2


def test_parse_film_room_search_forge_cdn_fallback_with_existing_hls() -> None:
    mock_payload = {
        "data": {
            "search": {
                "total": 1,
                "plays": [
                    {
                        "id": "play-200",
                        "gameDate": "2024-08-13",
                        "mediaPlayback": [
                            {
                                "id": "mb-200",
                                "title": "Highlight with HLS only",
                                "date": "2024-08-13",
                                "mediaPlaybackId": "f7071359-b8485b07-ba6767c1-csvm-diamondx64-asset",
                            }
                        ],
                        "playbacks": [
                            {
                                "name": "hlsStream",
                                "url": "https://media.mlb.com/stream.m3u8",
                                "bitrate": 0,
                                "width": 0,
                                "height": 0,
                            }
                        ],
                    }
                ],
            }
        }
    }
    df = parse_film_room_search(mock_payload)
    assert len(df) == 1
    row = df.to_dicts()[0]
    expected_url = (
        "https://mlb-cuts-diamond.mlb.com/FORGE/2024/2024-08/13/"
        "f7071359-b8485b07-ba6767c1-csvm-diamondx64-asset_1280x720_59_4000K.mp4"
    )
    assert row["best_mp4_url"] == expected_url
    assert row["hls_url"] == "https://media.mlb.com/stream.m3u8"
    assert len(row["playbacks"]) == 2
    playback_urls = [p["url"] for p in row["playbacks"]]
    assert "https://media.mlb.com/stream.m3u8" in playback_urls
    assert expected_url in playback_urls
