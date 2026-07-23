# Caching Guide

`polars-baseball` includes an opt-in file cache to avoid redundant network requests during large data queries.

## Caching Strategy

- **Default status**: Caching is disabled until you call `configure_cache()` or pass a file-backed context.
- **Storage location**: File cache data is stored in the directory you configure.
- **Storage format**: Cached tables are written as Parquet for fast I/O and columnar compression.

## Configuring the Cache Location

### Programmatic Configuration

Use `configure_cache` from `polars_baseball`:

```python
from pathlib import Path
from polars_baseball import configure_cache

custom_cache_path = Path("./my_project_cache")
configure_cache(custom_cache_path)
```

`configure_cache()` enables the package-level cache used by APIs called without an explicit `context=`.
For explicit lifecycle control, create a file-backed context instead:

```python
from pathlib import Path
from polars_baseball import BaseballContext
from polars_baseball._cache import FileCacheAdapter, NullCacheAdapter

context = BaseballContext.with_file_cache(Path("./my_project_cache"))
```

Use `NullCacheAdapter` for production services that need all caching controlled by the application.
Use `FileCacheAdapter` when you want to inject a file cache directly:

```python
from pathlib import Path
from polars_baseball import BaseballContext
from polars_baseball._cache import FileCacheAdapter, NullCacheAdapter
from polars_baseball._client import HttpClient

no_cache_context = BaseballContext(http=HttpClient(timeout=5.0, max_retries=0), cache=NullCacheAdapter())
file_cache_context = BaseballContext(cache=FileCacheAdapter(Path("./my_project_cache")))
```

Retries and BRef rate limiting are opt-in:

```python
from polars_baseball import BaseballContext
from polars_baseball._client import HttpClient

context = BaseballContext(
    http=HttpClient(timeout=10.0, max_retries=2, bref_requests_per_minute=10),
)
```

Use `cleanup` when a long-running script needs to close the package-level HTTP clients explicitly:

```python
import asyncio
from polars_baseball import cleanup

async def main() -> None:
    await cleanup()

if __name__ == "__main__":
    asyncio.run(main())
```

### Lifecycle & Concurrency in Web Services

The global default context (used when calling package APIs without `context=`) is a lazy singleton designed for CLI scripts. It does not write cache files unless `configure_cache()` has been called. It is not thread-safe or loop-safe in long-running concurrent apps (like FastAPI or Celery).

For web services, always initialize and inject a custom `BaseballContext` tied to your application's lifecycle:

```python
from pathlib import Path

from fastapi import FastAPI
from polars_baseball import BaseballContext

# tied to lifespan
async def lifespan(app: FastAPI):
    app.state.pb_context = BaseballContext.with_file_cache(Path("./service-cache"))
    try:
        yield
    finally:
        await app.state.pb_context.close()
```

### Environment Variable

`POLARS_BASEBALL_CACHE_DIR` only affects `FileCacheAdapter()` instances created without an explicit path.
Call `configure_cache()` or `BaseballContext.with_file_cache()` to enable file caching.

## Cache Behavior

- **Parameter-level matching**: The cache key is based on the function and exact arguments. Identical calls reuse cached results.
- **No subset matching**: A cached query for `statcast("2026-06-01", "2026-06-10")` is not reused for `statcast("2026-06-05", "2026-06-06")`.
- **Compiled datasets**: Lahman and Chadwick Register tables are cached as per-table Parquet files under `compiled-datasets/`.
- **Compiled dataset CDN**: Set `POLARS_BASEBALL_DATASETS_URL` to a hosted compiled dataset root. The client then downloads `dataset/table.parquet` files instead of compiling from upstream ZIP archives.

Internal `@cached` key builders receive keyword arguments (`**kw`):

```python
from polars_baseball._cache import cached, generate_cache_key


def standings_cache_key(**kw: object) -> str:
    season = kw.get("season")
    return generate_cache_key("standings", {"season": season})
```

The decorator passes resolved keyword arguments to key builder functions.
