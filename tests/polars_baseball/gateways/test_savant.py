from unittest.mock import MagicMock

import pytest

import polars_baseball.gateways.savant as savant_gateway
from polars_baseball.exceptions import UpstreamParseError
from polars_baseball.gateways.savant import SavantGateway


@pytest.fixture
def gateway() -> SavantGateway:
    ctx = MagicMock()
    return SavantGateway(ctx)


def test_verify_error_response_no_error(gateway: SavantGateway) -> None:
    """When 'error' not in first 200 chars, return None."""
    gateway._verify_error_response("col_a,col_b\n1,2\n")


def test_verify_error_response_error_column(gateway: SavantGateway) -> None:
    """When CSV has 'error' column with data, raise UpstreamParseError with message."""
    with pytest.raises(UpstreamParseError, match="some error msg"):
        gateway._verify_error_response("error\nsome error msg\n")


def test_verify_error_response_non_csv_with_error(gateway: SavantGateway) -> None:
    """When text contains 'error' but is not parseable CSV, raise UpstreamParseError."""
    with pytest.raises(UpstreamParseError, match="failed with an error row"):
        gateway._verify_error_response("error " * 100)


def test_verify_error_response_no_error_column(gateway: SavantGateway) -> None:
    """When CSV has an 'error' column but no rows, raise UpstreamParseError."""
    with pytest.raises(UpstreamParseError, match="failed with an error row"):
        gateway._verify_error_response("error,foo\n")


def test_verify_error_response_propagates_memory_error(gateway: SavantGateway, monkeypatch: pytest.MonkeyPatch) -> None:
    """MemoryError must NOT be swallowed by _verify_error_response."""

    def failing_read_csv(*args: object, **kwargs: object) -> object:
        raise MemoryError("OOM")

    monkeypatch.setattr(savant_gateway.pl, "read_csv", failing_read_csv)

    with pytest.raises(MemoryError):
        gateway._verify_error_response("error\nsome error\n")


def test_verify_error_response_propagates_os_error(gateway: SavantGateway, monkeypatch: pytest.MonkeyPatch) -> None:
    """OSError must NOT be swallowed by _verify_error_response."""

    def failing_read_csv(*args: object, **kwargs: object) -> object:
        raise OSError("disk full")

    monkeypatch.setattr(savant_gateway.pl, "read_csv", failing_read_csv)

    with pytest.raises(OSError):
        gateway._verify_error_response("error\nsome error\n")


@pytest.mark.asyncio
async def test_get_leaderboard_csv_and_html_fallback() -> None:
    from unittest.mock import AsyncMock

    from polars_baseball._client import HttpClient

    csv_data = "player_name,player_id,stat\nShohei Ohtani,660271,10\n"
    html_data = "<html><table><thead><tr><th>player_name</th><th>stat</th></tr></thead><tbody><tr><td>Mike Trout</td><td>8</td></tr></tbody></table></html>"

    http = AsyncMock(spec=HttpClient)
    http.get_text.side_effect = [csv_data, html_data]

    async def fake_get_or_fetch(key: object, fetcher: object, **kwargs: object) -> object:
        return await fetcher()  # type: ignore[misc]

    cache = MagicMock()
    cache.get_or_fetch = AsyncMock(side_effect=fake_get_or_fetch)
    ctx = MagicMock()
    ctx.http = http
    ctx.cache = cache

    gw = SavantGateway(ctx)

    # 1. CSV happy path
    df_csv = await gw.get_leaderboard("https://baseballsavant.mlb.com/leaderboard")
    assert df_csv.height == 1
    assert "player_name" in df_csv.columns

    # 2. HTML table fallback
    df_html = await gw.get_leaderboard("https://baseballsavant.mlb.com/leaderboard")
    assert df_html.height == 1
    assert "player_name" in df_html.columns
    assert df_html["player_name"][0] == "Mike Trout"


def test_parse_savant_leaderboard_empty() -> None:
    from polars_baseball.parsers.savant import parse_savant_leaderboard

    assert parse_savant_leaderboard("").is_empty()
    assert parse_savant_leaderboard(b"   ").is_empty()


def test_parse_savant_leaderboard_embedded_json() -> None:
    from polars_baseball.parsers.savant import parse_savant_leaderboard

    html = """
    <html><head><script>
    var data = [{"player_name": "Shohei Ohtani", "oaa": 12, "season": 2024}];
    </script></head><body></body></html>
    """
    df = parse_savant_leaderboard(html)
    assert df.height == 1
    assert "player_name" in df.columns
    assert df["player_name"][0] == "Shohei Ohtani"


def test_parse_savant_leaderboard_invalid_fails_fast() -> None:
    from polars_baseball.exceptions import UpstreamStructureChangedError
    from polars_baseball.parsers.savant import parse_savant_leaderboard

    with pytest.raises(UpstreamStructureChangedError):
        parse_savant_leaderboard("random plain text without comma or table")
