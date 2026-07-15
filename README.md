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

- **Polars-native data**: Most public APIs return `polars.DataFrame`; documented exceptions such as
  `standings()` return `list[polars.DataFrame]`.
- **Async-first engine**: Data-fetching APIs are `async def` and can be composed with your own
  async workflows.
- **Multiple providers**: Statcast, Baseball Savant, FanGraphs, Baseball Reference, Lahman,
  Retrosheet, MLB Stats API, and player ID workflows.
- **Built-in cache**: Repeated network requests are cached as Parquet files for large workflows.
- **Service-ready context**: `BaseballContext` lets long-running apps control HTTP and cache
  resources explicitly.

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
    df = await pb.statcast(start_dt="2024-05-06", end_dt="2024-05-06")
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
        start_dt="2024-05-06",
        end_dt="2024-05-06",
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
    request = pb.FanGraphsRequest.batting(
        start_season=2024,
        end_season=2024,
        qual=100,
        max_results=20,
    )
    df = await pb.fg_data(request)
    print(df.head(10))


if __name__ == "__main__":
    asyncio.run(main())
```

## Examples

Runnable examples live in [`examples/`](examples/):

- [`examples/statcast_pitch_mix.py`](examples/statcast_pitch_mix.py): Statcast pitch mix with Polars.
- [`examples/fangraphs_leaderboard.py`](examples/fangraphs_leaderboard.py): FanGraphs batting leaderboard.
- [`examples/mlb_schedule.py`](examples/mlb_schedule.py): MLB Stats API schedule query.
- [`examples/benchmark_statcast.py`](examples/benchmark_statcast.py): Conservative Statcast timing and memory benchmark.

## Benchmarking

Do not trust performance claims without a reproducible command. Start with:

```bash
python examples/benchmark_statcast.py --start-date 2024-04-01 --end-date 2024-04-07
```

The script reports row count, column count, wall time, and Python allocation peak measured by
`tracemalloc`. Use the same date range, cache state, Python version, and machine when comparing
against pandas-first workflows.

## Web Services & Concurrency

Calling package functions without `context` uses the implicit package-level `BaseballContext`.
That default context is convenient for scripts, but long-running concurrent services should manage
their own context and pass it into every API call.

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
        start_dt="2026-06-01",
        end_dt="2026-06-02",
        context=app.state.pb_context,
    )
    return {"rows": df.height}
```

## API Namespace Policy

The package root (`import polars_baseball as pb`) exposes only stable, commonly used public APIs.
Provider-specific and advanced functions remain available under `polars_baseball.apis.*`.

Modules prefixed with `_`, including `_schemas`, are internal implementation details and are not
part of the compatibility contract.

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

## Showcase

Projects using `polars-baseball`:

- MLB dashboard workflows
- Chinese baseball website data jobs
- Threads bot baseball data pipelines

## Contributing

See [CONTRIBUTING.md](.github/CONTRIBUTING.md) for development workflow and architecture notes.

## Author

Created and maintained by Nick.
