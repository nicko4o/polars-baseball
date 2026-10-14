"""Contract tests: events() returns a DataFrame without writing to disk."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock

import polars as pl
import pytest

from polars_baseball._client import HttpClient
from polars_baseball.apis.retrosheet import events
from polars_baseball.context import BaseballContext


@pytest.mark.asyncio
async def test_events_uses_supplied_context() -> None:
    mock_contents = '[{"name": "2026NYN.EVA"}, {"name": "2026NYN.EVN"}]'
    mock_eva = "team,player,event\nNYM,100,HR\n"
    mock_evn = "team,player,event\nNYM,100,SO\n"
    mock_http = AsyncMock(spec=HttpClient)

    def mock_get(url: str, **_kwargs: object) -> str:
        if "contents" in url:
            return mock_contents
        if "EVA" in url:
            return mock_eva
        return mock_evn

    mock_http.get_text.side_effect = mock_get
    ctx = BaseballContext(http=mock_http)

    result = await events(2026, game_type="regular", context=ctx)
    assert isinstance(result, pl.LazyFrame)
    df = result.collect()

    assert df["filename"].to_list() == ["2026NYN.EVA", "2026NYN.EVN"]
    assert df["content"].to_list() == [mock_eva.encode("utf-8"), mock_evn.encode("utf-8")]
    assert mock_http.get_text.await_count == 3


@pytest.mark.asyncio
async def test_events_returns_dataframe_with_raw_content() -> None:
    mock_contents = '[{"name": "2026NYN.EVA"}, {"name": "2026NYN.EVN"}]'
    mock_eva = "team,player,event\nNYM,100,HR\n"
    mock_evn = "team,player,event\nNYM,100,SO\n"

    mock_http = AsyncMock(spec=HttpClient)

    def mock_get(url: str, **_kwargs: object) -> str:
        if "contents" in url:
            return mock_contents
        if "EVA" in url:
            return mock_eva
        return mock_evn

    mock_http.get_text.side_effect = mock_get
    ctx = BaseballContext(http=mock_http)
    result = await events(2026, game_type="regular", context=ctx)

    assert isinstance(result, pl.LazyFrame)
    df = result.collect()
    assert df.schema == {
        "season": pl.Int64,
        "event_type": pl.String,
        "filename": pl.String,
        "content": pl.Binary,
    }
    assert df["season"].to_list() == [2026, 2026]
    assert df["event_type"].to_list() == ["regular", "regular"]
    assert df["filename"].to_list() == ["2026NYN.EVA", "2026NYN.EVN"]
    assert df["content"].to_list() == [mock_eva.encode("utf-8"), mock_evn.encode("utf-8")]


@pytest.mark.asyncio
async def test_events_does_not_write_to_disk(tmp_path: Path) -> None:
    mock_contents = '[{"name": "2026NYN.EVA"}]'
    mock_data = "team,player,event\nNYM,100,HR\n"

    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text.side_effect = [mock_contents, mock_data]
    ctx = BaseballContext(http=mock_http)

    cache_dir = ctx.cache.cache_dir
    await events(2026, game_type="regular", context=ctx)
    non_cache_files = [
        p for p in tmp_path.rglob("*") if cache_dir is not None and cache_dir not in p.parents and p != cache_dir
    ]

    assert len(non_cache_files) == 0, f"events() wrote files to disk outside cache: {non_cache_files}"


@pytest.mark.asyncio
async def test_events_deprecated_type_keyword() -> None:
    mock_contents = '[{"name": "2026NYN.EVA"}]'
    mock_data = "team,player,event\nNYM,100,HR\n"

    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text.side_effect = [mock_contents, mock_data]
    ctx = BaseballContext(http=mock_http)

    with pytest.raises(TypeError):
        await events(2026, type="regular", context=ctx)


@pytest.mark.asyncio
async def test_events_fail_fast_cancellation() -> None:
    import asyncio

    mock_contents = '[{"name": "2026NYN.EVA"}, {"name": "2026BOS.EVA"}]'
    cancelled = False

    async def mock_get_text(url: str, **kwargs: object) -> str:
        nonlocal cancelled
        if "contents" in url:
            return mock_contents
        if "2026NYN" in url:
            await asyncio.sleep(0.005)
            raise RuntimeError("Upstream event fetch failure")
        try:
            await asyncio.sleep(1.0)
            return "team,player,event\nBOS,100,HR\n"
        except asyncio.CancelledError:
            cancelled = True
            raise

    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(side_effect=mock_get_text)
    ctx = BaseballContext(http=mock_http)

    with pytest.raises(RuntimeError, match="Upstream event fetch failure"):
        await events(2026, game_type="regular", context=ctx, concurrency_limit=2)

    assert cancelled is True


@pytest.mark.asyncio
async def test_events_bounded_concurrency_admission() -> None:
    import asyncio

    contents = [{"name": f"2026TEAM{i}.EVA"} for i in range(5)]
    import json

    mock_contents = json.dumps(contents)

    active = 0
    peak = 0
    lock = asyncio.Lock()

    async def mock_get_text(url: str, **kwargs: object) -> str:
        nonlocal active, peak
        if "contents" in url:
            return mock_contents
        async with lock:
            active += 1
            if active > peak:
                peak = active
        await asyncio.sleep(0.01)
        async with lock:
            active -= 1
        return "team,player,event\nBOS,100,HR\n"

    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(side_effect=mock_get_text)
    ctx = BaseballContext(http=mock_http)

    limit = 2
    result = await events(2026, game_type="regular", context=ctx, concurrency_limit=limit)

    assert isinstance(result, pl.LazyFrame)
    assert peak <= limit
