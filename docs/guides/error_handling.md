> [!NOTE]
> All public exceptions inherit from `PolarsBaseballError`. Inspecting exception types allows application logic to distinguish between invalid caller parameters and upstream service issues.

# Error Handling & Production Resilience

This guide describes the exception hierarchy in `polars_baseball`, common error modes, and recommended patterns for handling errors in production services and data pipelines.

---

## Exception Hierarchy

All custom exceptions raised by `polars_baseball` are defined in `polars_baseball.exceptions` and follow a structured classification:

```text
PolarsBaseballError (Base)
├── ClientError (4xx equivalent)
│   └── InvalidParameterError
└── ServerError (5xx equivalent)
    ├── PolarsBaseballHttpError (has .status_code)
    ├── PolarsBaseballTransportError
    ├── UpstreamParseError
    │   ├── UpstreamStructureChangedError
    │   └── UpstreamDataCorruptedError
    ├── UpstreamUnavailableError
    ├── InvalidSchemaError
    └── CacheClearError
```

### Exception Reference

| Exception Class | Parent | Trigger Scenario |
| --- | --- | --- |
| `PolarsBaseballError` | `Exception` | Base class for all package errors. |
| `ClientError` | `PolarsBaseballError` | Caller error (invalid arguments or request payload). |
| `InvalidParameterError` | `ClientError`, `ValueError` | Parameter validation failure (e.g. invalid date format or out-of-range season). |
| `ServerError` | `PolarsBaseballError` | Upstream network, HTTP, or parser failure. |
| `PolarsBaseballHttpError` | `ServerError` | HTTP error returned from upstream (e.g. status 403, 404, 500, 503). |
| `PolarsBaseballTransportError` | `ServerError` | Network connection failure, timeout, or DNS resolution failure. |
| `UpstreamParseError` | `ServerError`, `RuntimeError` | Failed to parse upstream response body (HTML/JSON). |
| `UpstreamStructureChangedError` | `UpstreamParseError` | Upstream web layout or JSON payload schema changed. |
| `UpstreamDataCorruptedError` | `UpstreamParseError` | Downloaded data payload is malformed or incomplete. |
| `UpstreamUnavailableError` | `ServerError` | Upstream service returned an empty response or maintenance notice. |
| `InvalidSchemaError` | `ServerError` | Polars schema validation mismatch. |
| `CacheClearError` | `ServerError` | File cache deletion or write error. |

---

## Basic Error Handling Pattern

Use standard Python `try...except` blocks to handle caller errors vs. transient upstream network issues separately:

```python
import asyncio
from polars_baseball import statcast
from polars_baseball.exceptions import (
    ClientError,
    PolarsBaseballHttpError,
    PolarsBaseballTransportError,
    ServerError,
)

async def fetch_data() -> None:
    try:
        df = await statcast(start_date="2026-06-01", end_date="2026-06-02")
        print(f"Retrieved {df.height} rows.")
    except ClientError as err:
        print(f"Invalid caller request: {err}")
    except PolarsBaseballHttpError as err:
        print(f"HTTP Error {err.status_code}: {err}")
    except PolarsBaseballTransportError as err:
        print(f"Network connectivity error: {err}")
    except ServerError as err:
        print(f"Upstream server error: {err}")

if __name__ == "__main__":
    asyncio.run(fetch_data())
```

---

## Production Retry Strategy

When running automated pipelines or web endpoints, transient upstream errors (such as HTTP 502/503 or network timeouts) should be retried with exponential backoff.

> [!TIP]
> Do not retry `ClientError` or `InvalidParameterError` as caller errors will fail consistently without parameter changes.

```python
import asyncio
import logging
from typing import TypeVar, Callable, Awaitable
import polars as pl
import polars_baseball as pb
from polars_baseball.exceptions import ClientError, ServerError

logger = logging.getLogger(__name__)

T = TypeVar("T")

async def retry_async(
    func: Callable[[], Awaitable[T]],
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 2.0,
) -> T:
    delay = initial_delay
    for attempt in range(1, max_retries + 1):
        try:
            return await func()
        except ClientError:
            raise  # Do not retry invalid input errors
        except ServerError as err:
            if attempt == max_retries:
                logger.error("Final retry failed for upstream query.", exc_info=True)
                raise
            logger.warning(
                "Attempt %d/%d failed with error (%s). Retrying in %.1fs...",
                attempt, max_retries, err, delay
            )
            await asyncio.sleep(delay)
            delay *= backoff_factor
    raise RuntimeError("Unreachable")

async def main() -> None:
    df = await retry_async(
        lambda: pb.statcast(start_date="2026-06-01", end_date="2026-06-01")
    )
    print("Success, rows:", df.height)

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Managing Session Resources in Web Applications

In long-running web services (e.g. FastAPI, Starlette), wrap calls with `BaseballContext` to share connection pools, manage timeouts, and cleanly handle resource cleanup on shutdown.

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
import polars_baseball as pb
from polars_baseball.exceptions import ClientError, ServerError

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with pb.BaseballContext() as context:
        app.state.pb_context = context
        yield

app = FastAPI(lifespan=lifespan)

@app.get("/api/schedule")
async def get_schedule(date: str):
    try:
        df = await pb.mlb.schedule(
            start_date=date,
            end_date=date,
            context=app.state.pb_context
        )
        return {"count": df.height, "data": df.to_dicts()}
    except ClientError as err:
        raise HTTPException(status_code=400, detail=str(err))
    except ServerError as err:
        raise HTTPException(status_code=502, detail=f"Upstream provider failure: {err}")
```
