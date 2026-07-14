import json
from unittest.mock import AsyncMock

import polars as pl
import pytest

from polars_baseball._client import HttpClient
from polars_baseball.context import BaseballContext
from polars_baseball.exceptions import PolarsBaseballHttpError, UpstreamParseError
from polars_baseball.gateways.mlb import MlbStatsGateway


@pytest.mark.asyncio
async def test_mlb_stats_gateway_fetches_json_object() -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=json.dumps({"people": []}))
    gateway = MlbStatsGateway(BaseballContext(http=mock_http))

    df = await gateway.fetch(
        "https://statsapi.mlb.com/api/v1/people",
        None,
        "failed",
        lambda data: pl.DataFrame(data["people"]),
    )

    assert isinstance(df, pl.DataFrame)
    assert df.is_empty()


@pytest.mark.asyncio
async def test_mlb_stats_gateway_rejects_non_object_json() -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=json.dumps([]))
    gateway = MlbStatsGateway(BaseballContext(http=mock_http))

    with pytest.raises(UpstreamParseError, match="Expected dict"):
        await gateway.fetch(
            "https://statsapi.mlb.com/api/v1/people",
            None,
            "failed",
            lambda data: pl.DataFrame(),
        )


@pytest.mark.asyncio
async def test_mlb_stats_gateway_preserves_http_errors() -> None:
    http_error = PolarsBaseballHttpError("network failed", status_code=503)
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(side_effect=http_error)
    gateway = MlbStatsGateway(BaseballContext(http=mock_http))

    with pytest.raises(PolarsBaseballHttpError) as exc_info:
        await gateway.fetch(
            "https://statsapi.mlb.com/api/v1/people",
            None,
            "failed",
            lambda data: pl.DataFrame(),
        )

    assert exc_info.value is http_error
