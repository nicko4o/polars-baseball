from unittest.mock import AsyncMock

import polars as pl
import pytest

from polars_baseball._client import HttpClient
from polars_baseball.client import BaseballClient
from polars_baseball.exceptions import UpstreamUnavailableError

GAMELOG_ROW = b"20261025,0,Sun,NYA,AL,1,BOS,AL,1,5,4," + b"," * 150 + b"\n"

POSTSEASON_LOG_CASES: list[tuple[str, str, str]] = [
    ("world_series", "world_series_logs", "WS"),
    ("all_star", "all_star_game_logs", "AS"),
    ("wild_card", "wild_card_logs", "WC"),
    ("division_series", "division_series_logs", "DV"),
    ("lcs", "lcs_logs", "LC"),
]


@pytest.mark.asyncio
@pytest.mark.parametrize("label,method_name,suffix", POSTSEASON_LOG_CASES)
async def test_postseason_logs_success(label: str, method_name: str, suffix: str) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=GAMELOG_ROW)
    client = BaseballClient(http=mock_http)

    method = getattr(client.retrosheet, method_name)
    df = await method()

    assert isinstance(df, pl.DataFrame)
    assert df.height == 1
    assert df["visiting_team"][0] == "NYA"
    called_url = mock_http.get_text.call_args.args[0]
    assert suffix in called_url


@pytest.mark.asyncio
@pytest.mark.parametrize("label,method_name,suffix", POSTSEASON_LOG_CASES)
async def test_postseason_logs_empty_raises(label: str, method_name: str, suffix: str) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=b"")
    client = BaseballClient(http=mock_http)

    method = getattr(client.retrosheet, method_name)
    with pytest.raises(UpstreamUnavailableError, match="empty"):
        await method()
