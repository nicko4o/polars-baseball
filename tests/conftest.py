from collections.abc import Iterator
from pathlib import Path

import pytest

from polars_baseball._cache import global_cache


@pytest.fixture(autouse=True)
def isolated_polars_baseball_cache(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    cache_path = tmp_path / "polars_baseball-cache"
    monkeypatch.setenv("POLARS_BASEBALL_CACHE_DIR", str(cache_path))
    global_cache.reset()
    yield
    global_cache.reset()
