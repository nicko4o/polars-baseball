from unittest.mock import AsyncMock, MagicMock

import pytest

from polars_baseball._client import HttpClient
from polars_baseball.context import BaseballContext
from polars_baseball.gateways.savant import SavantGateway


@pytest.mark.asyncio
@pytest.mark.parametrize("response", ["", "<html><body>redirect</body></html>"])
async def test_get_optional_dataset_returns_none_for_unavailable_csv(response: str) -> None:
    http = AsyncMock(spec=HttpClient)
    http.get_text.return_value = response
    cache = MagicMock()
    cache.get.return_value = None
    context = BaseballContext(http=http, cache=cache)

    result = await SavantGateway(context).get_optional_dataset(
        "https://example.test/active-spin",
        {"year": "2026_spin-based"},
    )

    assert result is None
    cache.set.assert_not_called()
