from collections.abc import Iterator
from pathlib import Path

import pytest

from polars_baseball._cache import configure_cache


@pytest.fixture(autouse=True)
def isolated_polars_baseball_cache(tmp_path: Path) -> Iterator[None]:
    configure_cache(tmp_path / "polars_baseball-cache")
    yield
