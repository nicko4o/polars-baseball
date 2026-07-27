from collections.abc import Awaitable, Callable
from unittest.mock import AsyncMock

import polars as pl
import pytest

from polars_baseball._client import HttpClient
from polars_baseball.apis.retrosheet import (
    all_star_game_logs,
    division_series_logs,
    lcs_logs,
    wild_card_logs,
    world_series_logs,
)
from polars_baseball.context import BaseballContext
from polars_baseball.exceptions import UpstreamUnavailableError

GAMELOG_ROW = b"20261025,0,Sun,NYA,AL,1,BOS,AL,1,5,4," + b"," * 150 + b"\n"


_AsyncLogFunc = Callable[..., Awaitable[pl.DataFrame]]

POSTSEASON_LOG_FUNCS: list[tuple[str, _AsyncLogFunc, str]] = [
    ("world_series", world_series_logs, "WS"),
    ("all_star", all_star_game_logs, "AS"),
    ("wild_card", wild_card_logs, "WC"),
    ("division_series", division_series_logs, "DV"),
    ("lcs", lcs_logs, "LC"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("label,func,suffix", POSTSEASON_LOG_FUNCS)
async def test_postseason_logs_success(label: str, func: _AsyncLogFunc, suffix: str) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=GAMELOG_ROW)
    ctx = BaseballContext(http=mock_http)

    df = await func(context=ctx)

    assert isinstance(df, pl.DataFrame)
    assert df.height == 1
    assert df["visiting_team"][0] == "NYA"
    called_url = mock_http.get_text.call_args.args[0]
    assert suffix in called_url


@pytest.mark.asyncio
@pytest.mark.parametrize("label,func,suffix", POSTSEASON_LOG_FUNCS)
async def test_postseason_logs_empty_raises(label: str, func: _AsyncLogFunc, suffix: str) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=b"")
    ctx = BaseballContext(http=mock_http)

    with pytest.raises(UpstreamUnavailableError, match="empty"):
        await func(context=ctx)
