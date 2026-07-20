from collections.abc import Iterator
from pathlib import Path

import pytest

from polars_baseball import context as pb_context
from polars_baseball._cache import _set_default_cache_context_resolver, configure_cache


def silent_default_context() -> pb_context.BaseballContext:
    if pb_context._default_ctx is not None:
        return pb_context._default_ctx
    with pb_context._default_ctx_lock:
        if pb_context._default_ctx is None:
            pb_context._default_ctx = pb_context.BaseballContext()
    return pb_context._default_ctx


# Monkeypatch default_context to suppress DeprecationWarnings in tests
pb_context.default_context = silent_default_context
_set_default_cache_context_resolver(silent_default_context)


@pytest.fixture(autouse=True)
def isolated_polars_baseball_cache(tmp_path: Path) -> Iterator[None]:
    configure_cache(tmp_path / "polars_baseball-cache")
    yield
