import asyncio
from datetime import date
from unittest.mock import AsyncMock, MagicMock, patch

import httpx
import pytest

from polars_baseball._client import HttpClient
from polars_baseball._encoding import ensure_str
from polars_baseball._season import sanitize_date_range, statcast_date_range, validate_datestring
from polars_baseball.context import BaseballContext
from polars_baseball.exceptions import InvalidParameterError
from polars_baseball.parsers.savant import SavantCSVParser


def test_leap_year_feb29_is_valid() -> None:
    assert validate_datestring("2024-02-29") == date(2024, 2, 29)


def test_sanitize_date_range_with_leap_year() -> None:
    start, end = sanitize_date_range("2024-02-28", "2024-03-01")
    assert start == date(2024, 2, 28)
    assert end == date(2024, 3, 1)


def test_statcast_date_range_respects_leap_year_does_not_crash() -> None:
    results = list(statcast_date_range(date(2024, 3, 15), date(2024, 4, 5), step=5, verbose=False))
    assert len(results) >= 1


def test_validate_datestring_rejects_feb29_nonleap() -> None:
    with pytest.raises(InvalidParameterError):
        validate_datestring("2023-02-29")


def test_unicode_emoji_in_encoding() -> None:
    emoji = "⚾🔥👋"
    assert ensure_str(emoji) == emoji
    assert ensure_str(emoji.encode("utf-8")) == emoji


def test_unicode_japanese_in_encoding() -> None:
    japanese = "大谷翔平"
    assert ensure_str(japanese) == japanese
    assert ensure_str(japanese.encode("utf-8")) == japanese


def test_unicode_fullwidth_space_in_encoding() -> None:
    fullwidth = "\u3000"
    assert ensure_str(fullwidth) == fullwidth


def test_savant_csv_nan_values_do_not_crash() -> None:
    csv_data = "player_name,player_id,stat_value\nOhtani,660271,NaN\nTrout,545361,Infinity\nJudge,592450,-Infinity\n"
    parser = SavantCSVParser()
    df = parser.parse(csv_data)
    assert df.height == 3
    assert "player_name" in df.columns
    assert "stat_value" in df.columns


def test_savant_csv_empty_rows() -> None:
    csv_data = "player_name,player_id,year\nOhtani,660271,2026\n\nTrout,545361,2026\n"
    parser = SavantCSVParser()
    df = parser.parse(csv_data)
    assert df.height >= 2


def test_savant_csv_only_header() -> None:
    parser = SavantCSVParser()
    df = parser.parse("player_name,player_id,year\n")
    assert df.height == 0
    assert df.columns == ["player_name", "player_id", "year"]


def test_savant_csv_empty_string() -> None:
    parser = SavantCSVParser()
    df = parser.parse("")
    assert df.height == 0


def test_savant_csv_whitespace_only() -> None:
    parser = SavantCSVParser()
    df = parser.parse("   \n  \n")
    assert df.height == 0


@pytest.mark.asyncio
async def test_httpx_429_is_wrapped() -> None:
    client = HttpClient(max_retries=0, retry_backoff_base_seconds=0)
    error_response = MagicMock(spec=httpx.Response)
    error_response.status_code = 429
    error_response.raise_for_status.side_effect = httpx.HTTPStatusError(
        message="Too Many Requests",
        request=MagicMock(),
        response=error_response,
    )

    mock_httpx = MagicMock(spec=httpx.AsyncClient)
    mock_httpx.get = AsyncMock(return_value=error_response)

    from polars_baseball.exceptions import PolarsBaseballHttpError

    with patch.object(client, "_httpx_client", mock_httpx):
        with pytest.raises(PolarsBaseballHttpError) as exc_info:
            await client.get_text("https://baseballsavant.mlb.com/api")

    assert exc_info.value.status_code == 429
    assert mock_httpx.get.await_count == 1


@pytest.mark.asyncio
async def test_default_singleton_concurrent_tasks() -> None:
    BaseballContext._default_instance = None

    async def get_default() -> int:
        ctx = BaseballContext.default()
        return id(ctx)

    results = await asyncio.gather(*[get_default() for _ in range(10)])
    assert all(r == results[0] for r in results)

    BaseballContext._default_instance = None
