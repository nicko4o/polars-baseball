from unittest.mock import AsyncMock, MagicMock

import polars as pl
import pytest

from polars_baseball._client import HttpClient
from polars_baseball.context import BaseballContext
from polars_baseball.gateways.fangraphs import FanGraphsGateway

_HTML = (
    '<script id="__NEXT_DATA__" type="application/json">'
    '{"props":{"pageProps":{"dehydratedState":{"queries":['
    '{"queryKey":["leaders/major-league/data",{}],'
    '"state":{"data":{"data":[{"Name":"Example","playerid":1}]}}}'
    "]}}}}"
    "</script>"
)


async def _get_or_fetch(key: str, fetcher: object, **kwargs: object) -> pl.DataFrame:
    return await fetcher()  # type: ignore[misc]


@pytest.mark.asyncio
async def test_get_leaderboard_owns_fetch_cache_and_parse() -> None:
    http = AsyncMock(spec=HttpClient)
    http.get_text.return_value = _HTML
    cache = MagicMock()
    cache.get_or_fetch = AsyncMock(side_effect=_get_or_fetch)
    context = BaseballContext(http=http, cache=cache)

    result = await FanGraphsGateway(context).get_leaderboard(
        "https://example.test/leaders",
        {"season": 2026},
    )

    assert isinstance(result, pl.DataFrame)
    cache.get_or_fetch.assert_awaited_once()
    http.get_text.assert_awaited_once_with("https://example.test/leaders", params={"season": 2026})
