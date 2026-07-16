import logging
from collections.abc import Callable, Coroutine
from datetime import timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest

from polars_baseball._cache import FileCacheAdapter
from polars_baseball._client import HttpClient
from polars_baseball.context import BaseballContext
from polars_baseball.exceptions import UpstreamStructureChangedError
from polars_baseball.gateways.bref import BRefGateway
from polars_baseball.parsers.bref import BRefHTMLParser


@pytest.mark.asyncio
async def test_get_dataset_no_cache_empty_response() -> None:
    """1. Empty response with use_cache=False returns empty pl.DataFrame."""
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text.return_value = ""

    ctx = BaseballContext(http=mock_http, cache=MagicMock(spec=FileCacheAdapter))
    gateway = BRefGateway(ctx)

    df = await gateway.get_dataset("https://www.baseball-reference.com/dummy", use_cache=False)
    assert isinstance(df, pl.DataFrame)
    assert df.height == 0


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

    df = await gateway.get_dataset("https://www.baseball-reference.com/dummy", use_cache=True)
    assert isinstance(df, pl.DataFrame)
    assert df.height == 0


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
async def test_get_dataset_chain_failure_raises() -> None:
    """4. Parser/chain failure must fail fast and not be swallowed into an empty table (chain failure)."""
    mock_chain = MagicMock()
    mock_chain.execute.side_effect = UpstreamStructureChangedError("chain execute failed")

    ctx = BaseballContext(http=AsyncMock(spec=HttpClient), cache=MagicMock(spec=FileCacheAdapter))
    gateway = BRefGateway(ctx)

    with pytest.raises(UpstreamStructureChangedError, match="chain execute failed"):
        gateway._parse_response("raw_text", parser=None, chain=mock_chain)


@pytest.mark.asyncio
async def test_get_dataset_parser_failure_raises() -> None:
    """4. Parser/chain failure must fail fast and not be swallowed into an empty table (parser failure)."""
    mock_parser = MagicMock()
    mock_parser.parse.side_effect = ValueError("legacy parse failed")

    ctx = BaseballContext(http=AsyncMock(spec=HttpClient), cache=MagicMock(spec=FileCacheAdapter))
    gateway = BRefGateway(ctx)

    with pytest.raises(ValueError, match="legacy parse failed"):
        gateway._parse_response("raw_text", parser=mock_parser, chain=None)


@pytest.mark.asyncio
async def test_get_dataset_auto_chain_fails_and_falls_back_to_legacy_parser(caplog: pytest.LogCaptureFixture) -> None:
    """4. Auto-chain fallback to legacy parser when execution fails."""
    mock_parser = MagicMock(spec=BRefHTMLParser)
    mock_parser.parse.return_value = pl.DataFrame({"fallback": [1]})

    ctx = BaseballContext(http=AsyncMock(spec=HttpClient), cache=MagicMock(spec=FileCacheAdapter))
    gateway = BRefGateway(ctx)

    # Passing garbage_text that does not conform to the BRef HTML structure
    # will cause the auto-chain strategy to throw an exception,
    # triggering a fallback to mock_parser.parse.
    with caplog.at_level(logging.WARNING, logger="polars_baseball.gateways.bref"):
        df = gateway._parse_response("garbage_text", parser=mock_parser, chain=None)

    assert isinstance(df, pl.DataFrame)
    assert df.equals(pl.DataFrame({"fallback": [1]}))
    mock_parser.parse.assert_called_once_with("garbage_text")
    assert "BRef auto-chain failed; falling back to legacy parser" in caplog.text


@pytest.mark.asyncio
async def test_get_splits_no_cache_empty_html() -> None:
    """5. Get_splits boundary behavior when use_cache=False and raw HTML is empty."""
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text.return_value = ""

    ctx = BaseballContext(http=mock_http, cache=MagicMock(spec=FileCacheAdapter))
    gateway = BRefGateway(ctx)

    df_main, info, df_level = await gateway.get_splits("troutmi01", year=2026, use_cache=False)
    assert isinstance(df_main, pl.DataFrame)
    assert df_main.is_empty()
    assert isinstance(df_level, pl.DataFrame)
    assert df_level.is_empty()
    assert info == {"Position": "", "Bats": "", "Throws": ""}


@pytest.mark.asyncio
async def test_get_splits_cached_empty_html() -> None:
    """5. Get_splits boundary behavior when use_cache=True and cached HTML is empty."""
    mock_cache = MagicMock(spec=FileCacheAdapter)
    mock_cache.get_or_fetch = AsyncMock(return_value=pl.DataFrame())

    ctx = BaseballContext(http=AsyncMock(spec=HttpClient), cache=mock_cache)
    gateway = BRefGateway(ctx)

    df_main, info, df_level = await gateway.get_splits("troutmi01", year=2026, use_cache=True)
    assert isinstance(df_main, pl.DataFrame)
    assert df_main.is_empty()
    assert isinstance(df_level, pl.DataFrame)
    assert df_level.is_empty()
    assert info == {"Position": "", "Bats": "", "Throws": ""}


@pytest.mark.asyncio
async def test_get_splits_passes_params_to_cache() -> None:
    """5. Get_splits parameters are correctly passed to the cache adapter."""
    mock_cache = MagicMock(spec=FileCacheAdapter)
    mock_cache.get_or_fetch = AsyncMock(return_value=pl.DataFrame({"html": ["<html></html>"]}))

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

    mock_cache.get_or_fetch.assert_called_once()
    _, kwargs = mock_cache.get_or_fetch.call_args
    assert kwargs["max_age"] == max_age
    assert kwargs["force_update"] is True


@pytest.mark.asyncio
async def test_get_dataset_no_cache_success() -> None:
    """Test get_dataset with use_cache=False returning parsed data via chain."""
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text.return_value = "csv_data"

    mock_chain = MagicMock()
    mock_chain.execute.return_value.df = pl.DataFrame({"a": [1]})

    ctx = BaseballContext(http=mock_http, cache=MagicMock(spec=FileCacheAdapter))
    gateway = BRefGateway(ctx)

    df = await gateway.get_dataset("https://www.baseball-reference.com/dummy", use_cache=False, chain=mock_chain)
    assert df.equals(pl.DataFrame({"a": [1]}))


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
async def test_get_dataset_auto_chain_success() -> None:
    """Test get_dataset auto-chain execution succeeds."""
    mock_parser = MagicMock(spec=BRefHTMLParser)

    mock_chain = MagicMock()
    mock_chain.execute.return_value.df = pl.DataFrame({"auto": [42]})

    ctx = BaseballContext(http=AsyncMock(spec=HttpClient), cache=MagicMock(spec=FileCacheAdapter))
    gateway = BRefGateway(ctx)

    with patch("polars_baseball.gateways.bref._build_default_chain", return_value=mock_chain):
        df = gateway._parse_response("html_text", parser=mock_parser, chain=None)
        assert df.equals(pl.DataFrame({"auto": [42]}))


@pytest.mark.asyncio
async def test_fetch_and_parse_success() -> None:
    """Test _fetch_and_parse successfully fetches and parses data."""
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text.return_value = "col1,col2\n10,20\n"

    ctx = BaseballContext(http=mock_http, cache=MagicMock(spec=FileCacheAdapter))
    gateway = BRefGateway(ctx)

    df = await gateway._fetch_and_parse(
        "https://www.baseball-reference.com/dummy",
        params=None,
        headers=None,
        parser=None,
        chain=None,
    )
    assert df.equals(pl.DataFrame({"col1": [10], "col2": [20]}))


@pytest.mark.asyncio
async def test_get_splits_cache_fetcher_success() -> None:
    """Test get_splits cache fetcher executes and retrieves html from HTTP."""
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text.return_value = "<html><body><div class='players'><p>Position: OF</p></div></body></html>"

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

    _, info, _ = await gateway.get_splits("troutmi01", year=2026, use_cache=True)
    assert info["Position"] == "OF"
    mock_http.get_text.assert_called_once()
