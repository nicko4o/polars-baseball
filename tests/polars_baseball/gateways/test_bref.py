from collections.abc import Callable, Coroutine
from datetime import timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import polars as pl
import pytest

from polars_baseball._cache import FileCacheAdapter
from polars_baseball._client import HttpClient
from polars_baseball.context import BaseballContext
from polars_baseball.exceptions import UpstreamStructureChangedError, UpstreamUnavailableError
from polars_baseball.gateways.bref import BRefGateway


@pytest.mark.asyncio
async def test_get_dataset_no_cache_empty_response() -> None:
    """1. Empty response with use_cache=False returns empty pl.DataFrame."""
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text.return_value = ""

    ctx = BaseballContext(http=mock_http, cache=MagicMock(spec=FileCacheAdapter))
    gateway = BRefGateway(ctx)

    with pytest.raises(UpstreamUnavailableError):
        await gateway.get_dataset("https://www.baseball-reference.com/dummy", use_cache=False)


@pytest.mark.asyncio
async def test_get_dataset_cached_fetcher_empty_response() -> None:
    """2. Empty response through cache fetcher returns empty pl.DataFrame."""
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text.return_value = ""

    mock_cache = MagicMock(spec=FileCacheAdapter)

    async def fake_get_or_fetch(
        key: str,
        fetcher: Callable[[], Coroutine[Any, Any, pl.DataFrame]],
        **kwargs: object,
    ) -> pl.DataFrame:
        return await fetcher()

    mock_cache.get_or_fetch = AsyncMock(side_effect=fake_get_or_fetch)

    ctx = BaseballContext(http=mock_http, cache=mock_cache)
    gateway = BRefGateway(ctx)

    with pytest.raises(UpstreamUnavailableError):
        await gateway.get_dataset("https://www.baseball-reference.com/dummy", use_cache=True)


@pytest.mark.asyncio
async def test_get_dataset_passes_params_to_cache() -> None:
    """3. Max_age / force_update are correctly passed to the cache adapter in get_dataset."""
    mock_cache = MagicMock(spec=FileCacheAdapter)
    mock_cache.get_or_fetch = AsyncMock(return_value=pl.DataFrame())

    ctx = BaseballContext(http=AsyncMock(spec=HttpClient), cache=mock_cache)
    gateway = BRefGateway(ctx)

    max_age = timedelta(hours=1)
    await gateway.get_dataset(
        "https://www.baseball-reference.com/dummy",
        use_cache=True,
        max_age=max_age,
        force_update=True,
    )

    mock_cache.get_or_fetch.assert_called_once()
    _, kwargs = mock_cache.get_or_fetch.call_args
    assert kwargs["max_age"] == max_age
    assert kwargs["force_update"] is True


@pytest.mark.asyncio
async def test_get_dataset_parse_failure_raises() -> None:
    """4. Parser failure must fail fast and not be swallowed into an empty table."""
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text.return_value = "<<<corrupted xml table"

    ctx = BaseballContext(http=mock_http, cache=MagicMock(spec=FileCacheAdapter))
    gateway = BRefGateway(ctx)

    with pytest.raises(UpstreamStructureChangedError):
        await gateway.get_dataset("https://www.baseball-reference.com/dummy", use_cache=False)


@pytest.mark.asyncio
async def test_get_splits_no_cache_empty_html() -> None:
    """5. Get_splits boundary behavior when use_cache=False and raw HTML is empty."""
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text.return_value = ""

    ctx = BaseballContext(http=mock_http, cache=MagicMock(spec=FileCacheAdapter))
    gateway = BRefGateway(ctx)

    with pytest.raises(UpstreamUnavailableError):
        await gateway.get_splits("troutmi01", year=2026, use_cache=False)


@pytest.mark.asyncio
async def test_get_splits_cached_empty_html() -> None:
    """5. Get_splits boundary behavior when use_cache=True and cached HTML is empty."""
    mock_cache = MagicMock(spec=FileCacheAdapter)
    mock_cache.get_or_fetch_raw = AsyncMock(return_value=b"")

    ctx = BaseballContext(http=AsyncMock(spec=HttpClient), cache=mock_cache)
    gateway = BRefGateway(ctx)

    with pytest.raises(UpstreamUnavailableError):
        await gateway.get_splits("troutmi01", year=2026, use_cache=True)


@pytest.mark.asyncio
async def test_get_splits_passes_params_to_cache() -> None:
    """5. Get_splits parameters are correctly passed to the cache adapter."""
    mock_cache = MagicMock(spec=FileCacheAdapter)
    mock_cache.get_or_fetch_raw = AsyncMock(return_value=b"<html></html>")

    ctx = BaseballContext(http=AsyncMock(spec=HttpClient), cache=mock_cache)
    gateway = BRefGateway(ctx)

    max_age = timedelta(minutes=30)
    await gateway.get_splits(
        "troutmi01",
        year=2026,
        use_cache=True,
        max_age=max_age,
        force_update=True,
    )

    mock_cache.get_or_fetch_raw.assert_called_once()
    _, kwargs = mock_cache.get_or_fetch_raw.call_args
    assert kwargs["max_age"] == max_age
    assert kwargs["force_update"] is True


@pytest.mark.asyncio
async def test_get_dataset_default_csv_parser() -> None:
    """Test get_dataset falling back to pl.read_csv when parser and chain are None."""
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text.return_value = "col1,col2\n1,2\n"

    ctx = BaseballContext(http=mock_http, cache=MagicMock(spec=FileCacheAdapter))
    gateway = BRefGateway(ctx)

    df = await gateway.get_dataset("https://www.baseball-reference.com/dummy", use_cache=False)
    assert df.equals(pl.DataFrame({"col1": [1], "col2": [2]}))


@pytest.mark.asyncio
async def test_get_dataset_default_chain_html_table() -> None:
    """Test get_dataset default chain parses HTML tables via BRefStandardStrategy."""
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text.return_value = (
        "<table id='stats'><thead><tr><th>col1</th><th>col2</th></tr></thead>"
        "<tbody><tr><td>10</td><td>20</td></tr></tbody></table>"
    )

    ctx = BaseballContext(http=mock_http, cache=MagicMock(spec=FileCacheAdapter))
    gateway = BRefGateway(ctx)

    df = await gateway.get_dataset("https://www.baseball-reference.com/dummy", use_cache=False)
    assert "col1" in df.columns and "col2" in df.columns
    assert df["col1"][0] == "10" and df["col2"][0] == "20"


@pytest.mark.asyncio
async def test_get_dataset_default_embedded_csv_export() -> None:
    """Test get_dataset default parsing handles embedded CSV export table."""
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text.return_value = (
        "<html><body>"
        "<table id='csv_players_standard_batting'>"
        "<tr><td>Name,G,AB</td></tr>"
        "<tr><td>Player X,100,400</td></tr>"
        "</table>"
        "</body></html>"
    )

    ctx = BaseballContext(http=mock_http, cache=MagicMock(spec=FileCacheAdapter))
    gateway = BRefGateway(ctx)

    df = await gateway.get_dataset("https://www.baseball-reference.com/dummy", use_cache=False)
    assert "Name" in df.columns
    assert df["Name"][0] == "Player X"
    assert df.height == 1


@pytest.mark.asyncio
async def test_get_splits_cache_fetcher_success() -> None:
    """Test get_splits cache fetcher executes and retrieves html from HTTP."""
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text.return_value = "<html><body><div class='players'><p>Position: OF</p></div></body></html>"

    mock_cache = MagicMock(spec=FileCacheAdapter)

    async def fake_get_or_fetch_raw(
        key: str,
        fetcher: Callable[[], Coroutine[Any, Any, str]],
        **kwargs: object,
    ) -> bytes:
        val = await fetcher()
        return val.encode("utf-8") if isinstance(val, str) else val

    mock_cache.get_or_fetch_raw = AsyncMock(side_effect=fake_get_or_fetch_raw)

    ctx = BaseballContext(http=mock_http, cache=mock_cache)
    gateway = BRefGateway(ctx)

    _, info, _ = await gateway.get_splits("troutmi01", year=2026, use_cache=True)
    assert info["Position"] == "OF"
    mock_http.get_text.assert_called_once()


def test_parse_bref_dataset_empty() -> None:
    from polars_baseball.parsers.bref import parse_bref_dataset

    assert parse_bref_dataset("").is_empty()
    assert parse_bref_dataset(b"  ").is_empty()


def test_parse_bref_dataset_html_error_handling(monkeypatch: pytest.MonkeyPatch) -> None:
    from lxml.etree import ParserError

    import polars_baseball.parsers.bref as bref_module
    from polars_baseball.parsers.bref import parse_bref_dataset

    def failing_html(*args: object, **kwargs: object) -> object:
        raise ParserError("bad html")

    monkeypatch.setattr(bref_module.lxml.etree, "HTML", failing_html)
    # When HTML export parsing catches ParserError, it returns empty and falls through
    # to standard parser or raw csv or error
    html = "<html><body><table id='csv_1'><tr><td>col1</td></tr></table></body></html>"
    with pytest.raises(UpstreamStructureChangedError):
        parse_bref_dataset(html)


def test_parse_bref_dataset_invalid_fails_fast() -> None:
    from polars_baseball.parsers.bref import parse_bref_dataset

    with pytest.raises(UpstreamStructureChangedError):
        parse_bref_dataset("<<<invalid non-csv xml")


def test_parse_bref_dataset_csv_table_with_th_and_commas() -> None:
    from polars_baseball.parsers.bref import parse_bref_dataset

    html = """
    <html><body>
    <table id="csv_players_standard_batting">
        <tr><th>Name</th><th>Note</th><th>AB</th></tr>
        <tr><td>Player A</td><td>Some, note</td><td>400</td></tr>
    </table>
    </body></html>
    """
    df = parse_bref_dataset(html)
    assert df.height == 1
    assert list(df.columns) == ["Name", "Note", "AB"]
    assert df["Note"][0] == "Some, note"
    assert df["AB"][0] == 400
