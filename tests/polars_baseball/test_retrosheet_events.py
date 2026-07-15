"""Contract tests: events() returns a DataFrame without writing to disk."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, patch

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
    mock_http.get_text.side_effect = [mock_contents, mock_eva, mock_evn]
    ctx = BaseballContext(http=mock_http)

    with patch(
        "polars_baseball.apis.retrosheet.default_context",
        side_effect=AssertionError("default_context must not be used when context is supplied"),
    ):
        result = await events(2026, "regular", context=ctx)

    assert result["filename"].to_list() == ["2026NYN.EVA", "2026NYN.EVN"]
    assert result["content"].to_list() == [mock_eva.encode("utf-8"), mock_evn.encode("utf-8")]
    assert mock_http.get_text.await_count == 3


@pytest.mark.asyncio
async def test_events_returns_dataframe_with_raw_content() -> None:
    mock_contents = '[{"name": "2026NYN.EVA"}, {"name": "2026NYN.EVN"}]'
    mock_eva = "team,player,event\nNYM,100,HR\n"
    mock_evn = "team,player,event\nNYM,100,SO\n"

    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text.side_effect = [mock_contents, mock_eva, mock_evn]

    with patch("polars_baseball.apis.retrosheet.default_context", return_value=BaseballContext(http=mock_http)):
        result = await events(2026, "regular")

    assert isinstance(result, pl.DataFrame)
    assert result.schema == {
        "season": pl.Int64,
        "event_type": pl.String,
        "filename": pl.String,
        "content": pl.Binary,
    }
    assert result["season"].to_list() == [2026, 2026]
    assert result["event_type"].to_list() == ["regular", "regular"]
    assert result["filename"].to_list() == ["2026NYN.EVA", "2026NYN.EVN"]
    assert result["content"].to_list() == [mock_eva.encode("utf-8"), mock_evn.encode("utf-8")]


@pytest.mark.asyncio
async def test_events_does_not_write_to_disk(tmp_path: Path) -> None:
    mock_contents = '[{"name": "2026NYN.EVA"}]'
    mock_data = "team,player,event\nNYM,100,HR\n"

    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text.side_effect = [mock_contents, mock_data]

    with patch("polars_baseball.apis.retrosheet.default_context", return_value=BaseballContext(http=mock_http)):
        cwd_before = set(tmp_path.rglob("*"))
        await events(2026, "regular")
        cwd_after = set(tmp_path.rglob("*"))

    assert cwd_before == cwd_after, "events() wrote files to disk"
