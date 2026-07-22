# polars-baseball

[![PyPI version](https://img.shields.io/pypi/v/polars-baseball.svg)](https://pypi.org/project/polars-baseball/)
[![Python versions](https://img.shields.io/pypi/pyversions/polars-baseball.svg)](https://pypi.org/project/polars-baseball/)
[![CI](https://github.com/nicko4o/polars-baseball/actions/workflows/pytest.yml/badge.svg)](https://github.com/nicko4o/polars-baseball/actions)
[![Codecov](https://img.shields.io/codecov/c/github/nicko4o/polars-baseball)](https://codecov.io/gh/nicko4o/polars-baseball)
[![License](https://img.shields.io/pypi/l/polars-baseball.svg)](https://github.com/nicko4o/polars-baseball/blob/main/LICENSE)
[![Downloads](https://img.shields.io/pypi/dm/polars-baseball.svg)](https://pypi.org/project/polars-baseball/)

Languages: [English](README.md) | [Traditional Chinese](README.zh-TW.md)

`polars-baseball` is **The unified Polars-native baseball data SDK**: a typed, async-first Python
library for retrieving MLB and baseball analytics data from Statcast, Baseball Savant, FanGraphs,
Baseball Reference, Lahman, Retrosheet, and the MLB Stats API.

If you searched for `python baseball data`, `python statcast`, `fangraphs python`,
`baseball savant api`, `pybaseball alternative`, or `polars dataframe baseball`, this project is
built for the workflow where data should land directly in `polars.DataFrame` instead of going
through pandas first.

## Why use polars-baseball instead of pybaseball?

`pybaseball` is useful and established. `polars-baseball` is aimed at a different execution model:
async data ingestion, native Polars output, and one consistent entry point across multiple baseball
data providers.

| Feature | pybaseball | polars-baseball |
| --- | --- | --- |
| Polars native | No | Yes |
| Async data fetching | No | Yes |
| Statcast / Baseball Savant | Yes | Yes |
| FanGraphs | Yes | Yes |
| MLB Stats API | Limited | Yes |
| Lahman / Retrosheet workflows | Partial | Yes |
| Built-in cache | Partial | Yes |
| Typed public API | Partial | Yes |

Typical pandas-first workflow:

```text
pybaseball -> pandas -> convert to Polars -> analysis
```

`polars-baseball` workflow:

```text
polars-baseball -> Polars -> analysis
```

## Key Features

- **Polars-native data**: Public data-fetching APIs return `polars.DataFrame` unless an API
  reference explicitly documents a non-tabular contract.
- **Async-first engine**: Data-fetching APIs are `async def` and can be composed with your own
  async workflows.
- **Multiple providers**: Statcast, Baseball Savant, FanGraphs, Baseball Reference, Lahman,
  Retrosheet, MLB Stats API, and player ID workflows.
- **Opt-in file cache**: Large workflows can cache repeated network requests as Parquet files.
- **Service-ready context**: `BaseballContext` lets long-running apps control HTTP and cache
  resources explicitly.
- **Explicit HTTP policy**: `HttpClient` exposes timeout, retry, and BRef rate-limit settings.

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

To run visualization examples:

```bash
pip install "polars-baseball[plot]"
```

## Quick Start

### Statcast pitch-level data

```python
import asyncio

import polars_baseball as pb


async def main() -> None:
    df = await pb.statcast(start_date="2026-06-01", end_date="2026-06-01")
    print(df.head(5))


if __name__ == "__main__":
    asyncio.run(main())
```

### Aggregate directly with Polars

```python
import asyncio

import polars as pl
import polars_baseball as pb


async def main() -> None:
    df = await pb.statcast_pitcher(
        start_date="2026-06-01",
        end_date="2026-06-01",
        # Use pb.playerid_lookup("Judge", "Aaron") to find player IDs
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

### FanGraphs leaderboard

```python
import asyncio

import polars_baseball as pb


async def main() -> None:
    df = await pb.fangraphs.batting(
        start_season=2026,
        end_season=2026,
        qual=100,
        max_results=20,
    )
    print(df.head(10))


if __name__ == "__main__":
    asyncio.run(main())
```

## Examples

### Scripts (CLI-ready)

Runnable `.py` examples live in [`examples/`](examples/):

- [`examples/statcast_pitch_mix.py`](examples/statcast_pitch_mix.py): Statcast pitch mix with Polars.
- [`examples/fangraphs_leaderboard.py`](examples/fangraphs_leaderboard.py): FanGraphs batting leaderboard.
- [`examples/mlb_schedule.py`](examples/mlb_schedule.py): MLB Stats API schedule query.

### Notebooks (interactive)

Interactive Jupyter notebooks live in [`notebooks/`](notebooks/):

- [`notebooks/statcast_pitch_mix_demo.ipynb`](notebooks/statcast_pitch_mix_demo.ipynb): Statcast pitch mix, velocity leaders, batted-ball outcomes.
- [`notebooks/fangraphs_leaderboard_demo.ipynb`](notebooks/fangraphs_leaderboard_demo.ipynb): FanGraphs batting leaderboard with sabermetric filters.
- [`notebooks/mlb_schedule_demo.ipynb`](notebooks/mlb_schedule_demo.ipynb): MLB schedule, standings, rosters, and team metadata.
## Benchmarking

Do not trust performance claims without a reproducible command:

```bash
python -m benchmarks run statcast_1week
```

List available profiles:

```bash
python -m benchmarks run list
```

Full command reference:

```text
python -m benchmarks run <profile> [--json] [--json-file PATH] [--baseline] [--fail-if-regression]
python -m benchmarks baseline show
python -m benchmarks baseline clear
```

The runner reports wall time, CPU time, peak Python memory (via `tracemalloc`), GC collections,
and result shape. Use the `--baseline` flag to save results and compare against historical data.
Use the same date range, cache state, Python version, and machine when comparing
against pandas-first workflows.

## Web Services & Concurrency

Calling package functions without `context` uses the implicit package-level `BaseballContext`.
That default context is convenient for scripts and does not write cache files unless
`configure_cache()` has been called. Long-running concurrent services should manage their own
context and pass it into every API call.

```python
from contextlib import asynccontextmanager

from fastapi import FastAPI

import polars_baseball as pb


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with pb.BaseballContext() as context:
        app.state.pb_context = context
        yield


app = FastAPI(lifespan=lifespan)


@app.get("/statcast")
async def get_statcast() -> dict[str, int]:
    df = await pb.statcast(
        start_date="2026-06-01",
        end_date="2026-06-02",
        context=app.state.pb_context,
    )
    return {"rows": df.height}
```

## API Namespace Policy

The package root (`import polars_baseball as pb`) exposes core convenience APIs and provider
namespaces. Use `pb.fangraphs`, `pb.savant`, and `pb.mlb` for provider-specific workflows.
Lahman, Retrosheet, Baseball Reference, and player ID workflows remain available from the package root.

Modules prefixed with `_`, including `_schemas`, are internal implementation details and are not part
of the compatibility contract.

## Documentation

- [Documentation](docs/index.md)
- [API Use-Case Index](docs/api_index.md): choose the right API by task.

## Showcase

Projects using `polars-baseball`:

- MLB dashboard workflows
- Chinese baseball website data jobs
- Threads bot baseball data pipelines

## Contributing

See [CONTRIBUTING.md](.github/CONTRIBUTING.md) for development workflow and architecture notes.

## Author

Created and maintained by Nick.
