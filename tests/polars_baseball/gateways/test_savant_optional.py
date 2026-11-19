from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from polars_baseball._client import HttpClient
from polars_baseball.client import BaseballClient
from polars_baseball.gateways.savant import SavantGateway


@pytest.mark.asyncio
@pytest.mark.parametrize("response", ["", "<html><body>redirect</body></html>"])
async def test_get_optional_dataset_returns_none_for_unavailable_csv(response: str) -> None:
    http = AsyncMock(spec=HttpClient)
    http.get_text.return_value = response
    cache = MagicMock()
    cache.get.return_value = None
    context = BaseballClient(http=http, cache=cache)

    result = await SavantGateway(context).get_optional_dataset(
        "https://example.test/active-spin",
        {"year": "2026_spin-based"},
    )

    assert result is None
    cache.set.assert_not_called()


@pytest.mark.asyncio
async def test_get_optional_dataset_coalesces_concurrent_misses(tmp_path: Path) -> None:
    import asyncio

    from polars_baseball._cache import FileCacheAdapter

    calls = 0

    async def delayed_csv(url: str, *, params: object = None, headers: object = None) -> str:
        nonlocal calls
        calls += 1
        await asyncio.sleep(0.02)
        return "player_id,val\n1,42\n"

    http = AsyncMock(spec=HttpClient)
    http.get_text.side_effect = delayed_csv
    context = BaseballClient(http=http, cache=FileCacheAdapter(tmp_path))
    gateway = SavantGateway(context)

    results = await asyncio.gather(
        gateway.get_optional_dataset("https://example.test/active-spin", {"year": "2026"}),
        gateway.get_optional_dataset("https://example.test/active-spin", {"year": "2026"}),
        gateway.get_optional_dataset("https://example.test/active-spin", {"year": "2026"}),
    )

    assert calls == 1
    assert all(df is not None and df["val"][0] == 42 for df in results)
