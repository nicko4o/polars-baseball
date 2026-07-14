# polars-baseball

Languages: [English](README.md) | [Traditional Chinese](README.zh-TW.md)

`polars-baseball` is a modern asynchronous Python library for retrieving baseball data. It is built around
Polars, where most public data APIs return `polars.DataFrame` objects (with documented exceptions such as `standings()`
returning other shapes), and supports Statcast, Baseball Reference, FanGraphs, Lahman,
Retrosheet, MLB Stats API, and player ID workflows.

---

## Key Features

- **Polars Core**: Most public APIs return native `polars.DataFrame` objects (with `standings()` returning `list[polars.DataFrame]`) for filtering, aggregation, and export.
- **Async-First Engine**: Data-fetching APIs are asynchronous and should be called with `await` or `asyncio.run()`.
- **Flexible Concurrency**: Support for custom context configuration to isolate resources in multi-threaded/loop environments.
- **Automatic Cache**: Built-in file caching reduces repeated network requests for large workflows.

---

## Installation

```bash
pip install polars-baseball
```

For local development:

```bash
git clone https://github.com/nicko4o/polars-baseball
cd polars-baseball
uv sync --all-extras
```

To run the visualization examples, install the optional example dependencies:

```bash
pip install "polars-baseball[plot]"
```

---

## Quick Start

### 1. Statcast Queries

```python
import asyncio

import polars_baseball as pb


async def main() -> None:
    df = await pb.statcast(start_dt="2024-05-06", end_dt="2024-05-06")
    print(df.head(5))

    darvish_df = await pb.statcast_pitcher(
        start_dt="2024-05-06",
        end_dt="2024-05-06",
        player_id=506433,
    )
    print(darvish_df.head(5))


if __name__ == "__main__":
    asyncio.run(main())
```

### 2. Aggregate with Polars

```python
import asyncio

import polars as pl
import polars_baseball as pb


async def main() -> None:
    darvish_df = await pb.statcast_pitcher(
        start_dt="2024-05-06",
        end_dt="2024-05-06",
        player_id=506433,
    )
    summary = (
        darvish_df
        .group_by("pitch_type")
        .agg(pl.col("release_speed").mean().alias("mean_speed"))
    )
    print(summary)


if __name__ == "__main__":
    asyncio.run(main())
```

### 3. Top Prospects

```python
import asyncio

import polars_baseball as pb


async def main() -> None:
    prospects = await pb.top_prospects(team_name="mets")
    print(prospects.head(5))


if __name__ == "__main__":
    asyncio.run(main())
```

### 4. Interactive Data Visualization

`polars-baseball` does not provide a plotting API. This example passes the returned `polars.DataFrame` to hvPlot.

```python
import asyncio

import hvplot.polars  # noqa: F401
import polars_baseball as pb


async def main() -> None:
    df = await pb.statcast(start_dt="2024-05-06", end_dt="2024-05-06")
    chart = (
        df
        .filter(df["hc_x"].is_not_null() & df["hc_y"].is_not_null())
        .plot.scatter(
            x="hc_x",
            y="hc_y",
            by="events",
            invert_y=True,
        )
    )
    print(chart)


if __name__ == "__main__":
    asyncio.run(main())
```

## Web Services & Concurrency (FastAPI, Gunicorn, Celery)

By default, calling package functions without a `context` parameter will fallback to an implicit package-level global singleton `BaseballContext`. **This global default context is not guaranteed to be thread-safe or loop-safe in long-running concurrent environments.**

When deploying `polars-baseball` inside concurrent web services (such as FastAPI, Gunicorn, or Celery workers), you **must** explicitly manage the lifespan of `BaseballContext` and pass it to all API calls.

### FastAPI lifespan Example

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
import polars_baseball as pb

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Initialize a dedicated context bound to the app's event loop
    app.state.pb_context = pb.BaseballContext()
    try:
        yield
    finally:
        # Properly clean up HTTP connections
        await app.state.pb_context.http.close()

app = FastAPI(lifespan=lifespan)

@app.get("/statcast")
async def get_statcast():
    df = await pb.statcast(
        start_dt="2026-06-01",
        end_dt="2026-06-02",
        context=app.state.pb_context,
    )
    return df.to_dicts()
```

---

## API Namespace Policy

The package root (`import polars_baseball as pb`) exposes only the stable, commonly used public API. Provider-specific and advanced functions remain available from `polars_baseball.apis.*`.

Modules prefixed with `_`, including `_schemas`, are internal implementation details and are not part of the compatibility contract.

---

## Documentation

- [English documentation](docs/)
- [Traditional Chinese documentation](docs/zh-tw/)
- [Caching Guide](docs/caching.md)
- [Jupyter Notebook Usage](docs/jupyter.md)
- [Data Visualization Guide](docs/plotting.md)
- [Statcast API](docs/statcast.md)
- [Player ID Lookup](docs/playerid_lookup.md)
- [MLB Stats API](docs/mlb_api.md)
- [Savant Gamefeed API](docs/savant_gamefeed.md)
- [Prospect Rankings](docs/prospect_rankings.md)

---

## Contributing

See [CONTRIBUTING.md](.github/CONTRIBUTING.md) for the development workflow and architecture notes.

---

## Author

Created and maintained by Nick.
