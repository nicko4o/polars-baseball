# Caching Guide

`polars-baseball` includes a file cache to avoid redundant network requests during large data queries.

## Caching Strategy

- **Default status**: Caching is enabled by default.
- **Storage location**: Cached data is stored under `~/.polars_baseball/cache` unless configured otherwise.
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

The global default context (used when calling package APIs without `context=`) is a lazy singleton designed for CLI scripts. It is not thread-safe or loop-safe in long-running concurrent apps (like FastAPI or Celery).

For web services, always initialize and inject a custom `BaseballContext` tied to your application's lifecycle:

```python
from fastapi import FastAPI
from polars_baseball import BaseballContext

# tied to lifespan
async def lifespan(app: FastAPI):
    app.state.pb_context = BaseballContext()
    try:
        yield
    finally:
        await app.state.pb_context.close()
```

### Environment Variable

```bash
export POLARS_BASEBALL_CACHE_DIR="/path/to/your/custom/cache"
```

## Cache Behavior

- **Parameter-level matching**: The cache key is based on the function and exact arguments. Identical calls reuse cached results.
- **No subset matching**: A cached query for `statcast("2024-05-01", "2024-05-10")` is not reused for `statcast("2024-05-05", "2024-05-06")`.
- **Compiled datasets**: Lahman and Chadwick Register tables are cached as per-table Parquet files under `compiled-datasets/`.
- **Compiled dataset CDN**: Set `POLARS_BASEBALL_DATASETS_URL` to a hosted compiled dataset root. The client then downloads `dataset/table.parquet` files instead of compiling from upstream ZIP archives.

## Maintainer Notes

Internal `@cached` and `@cached_list` key builders use `CacheCallArgs`:

```python
from polars_baseball._cache import CacheCallArgs, cached, generate_cache_key


def standings_cache_key(call: CacheCallArgs) -> str:
    season = call.argument("season", int)
    return generate_cache_key("standings", {"season": season})
```

The decorator resolves only the standard `context` and `force_update` argument names. Key and max-age callbacks must accept one `CacheCallArgs` parameter; old callback forms such as `lambda season: ...`, `**kwargs`, or `ctx` / `_ctx` context aliases are not supported.
