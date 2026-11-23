# polars-baseball

[![PyPI version](https://img.shields.io/pypi/v/polars-baseball.svg)](https://pypi.org/project/polars-baseball/)
[![Python versions](https://img.shields.io/pypi/pyversions/polars-baseball.svg)](https://pypi.org/project/polars-baseball/)
[![CI](https://github.com/nicko4o/polars-baseball/actions/workflows/pytest.yml/badge.svg)](https://github.com/nicko4o/polars-baseball/actions)
[![Codecov](https://img.shields.io/codecov/c/github/nicko4o/polars-baseball)](https://codecov.io/gh/nicko4o/polars-baseball)
[![License](https://img.shields.io/pypi/l/polars-baseball.svg)](https://github.com/nicko4o/polars-baseball/blob/main/LICENSE)
[![Downloads](https://img.shields.io/pypi/dm/polars-baseball.svg)](https://pypi.org/project/polars-baseball/)

Languages: [English](README.md) | [Traditional Chinese](README.zh-TW.md)

`polars-baseball` is a typed, async-first Python library for retrieving baseball analytics data from Statcast, Baseball Savant, FanGraphs, Baseball Reference, Lahman, Retrosheet, and the MLB Stats API directly into `polars.DataFrame`.

## Key Features

- **Polars-native & Async-first**: Every data-fetching API is `async def` and returns `polars.DataFrame` (or `pl.LazyFrame` / `list[pl.DataFrame]` where documented).
- **Unified Client**: `BaseballClient` manages HTTP connection pooling, retries, rate limiting (`HttpClient`), and optional local Parquet caching across 7 providers (`savant`, `fangraphs`, `bref`, `mlb`, `retrosheet`, `lahman`, `lookup`).

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

## Quick Start

```python
import asyncio
import polars as pl
from polars_baseball import BaseballClient


async def main() -> None:
    async with BaseballClient() as client:
        df = await client.savant.pitcher(
            start_date="2026-06-01",
            end_date="2026-06-01",
            # Use await client.lookup.playerid_lookup("Judge", "Aaron") to find player IDs
            player_id=506433,
        )
        summary = df.group_by("pitch_type").agg(
            pl.col("release_speed").mean().alias("mean_speed"),
            pl.len().alias("pitch_count"),
        )
        print(summary.sort("pitch_count", descending=True))


if __name__ == "__main__":
    asyncio.run(main())
```

Runnable scripts live in [`examples/`](examples/) and interactive notebooks in [`notebooks/`](notebooks/):

- [`examples/statcast_pitch_mix.py`](examples/statcast_pitch_mix.py) / [`notebooks/statcast_pitch_mix_demo.ipynb`](notebooks/statcast_pitch_mix_demo.ipynb)
- [`examples/fangraphs_leaderboard.py`](examples/fangraphs_leaderboard.py) / [`notebooks/fangraphs_leaderboard_demo.ipynb`](notebooks/fangraphs_leaderboard_demo.ipynb)
- [`examples/mlb_schedule.py`](examples/mlb_schedule.py) / [`notebooks/mlb_schedule_demo.ipynb`](notebooks/mlb_schedule_demo.ipynb)

## Web Services & Concurrency

Long-running services should manage one `BaseballClient` per application lifespan:

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
import polars_baseball as pb


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with pb.BaseballClient() as client:
        app.state.pb_client = client
        yield


app = FastAPI(lifespan=lifespan)


@app.get("/statcast")
async def get_statcast() -> dict[str, int]:
    client: pb.BaseballClient = app.state.pb_client
    df = await client.savant.statcast(start_date="2026-06-01", end_date="2026-06-02")
    return {"rows": df.height}
```

## Benchmarking

```bash
python -m benchmarks run list
python -m benchmarks run statcast_7day_cold [--baseline] [--fail-if-regression]
```

## Documentation & Governance

- [Documentation Home & API Index](docs/index.md)
- [Maintaining Guide](docs/MAINTAINING.md)
- [Contributing](.github/CONTRIBUTING.md) · [Security Policy](.github/SECURITY.md)

## Data Attribution & Best-Effort Notice

`polars-baseball` does not claim ownership of upstream datasets:

- **Retrosheet**: The information used here was obtained free of charge from and is copyrighted by Retrosheet ([www.retrosheet.org](https://www.retrosheet.org)).
- **Statcast & MLB Stats API**: Major League Baseball / Baseball Savant.
- **FanGraphs & Baseball Reference**: Rely on web scraping behind Cloudflare Turnstile and strict rate limits; access is **best-effort**. Configure `bref_requests_per_minute`, pass `CF_CLEARANCE`/`CF_COOKIE` via `extra_headers`, or use local Parquet caching.
- **Lahman**: Lahman's Baseball Database by Sean Lahman.

## Citation & License

Cite via [`CITATION.cff`](CITATION.cff). Licensed under the [MIT License](LICENSE) by Nick.
