# polars-baseball

[![PyPI version](https://img.shields.io/pypi/v/polars-baseball.svg)](https://pypi.org/project/polars-baseball/)
[![Python versions](https://img.shields.io/pypi/pyversions/polars-baseball.svg)](https://pypi.org/project/polars-baseball/)
[![CI](https://github.com/nicko4o/polars-baseball/actions/workflows/pytest.yml/badge.svg)](https://github.com/nicko4o/polars-baseball/actions)
[![Codecov](https://img.shields.io/codecov/c/github/nicko4o/polars-baseball)](https://codecov.io/gh/nicko4o/polars-baseball)
[![License](https://img.shields.io/pypi/l/polars-baseball.svg)](https://github.com/nicko4o/polars-baseball/blob/main/LICENSE)
[![Downloads](https://img.shields.io/pypi/dm/polars-baseball.svg)](https://pypi.org/project/polars-baseball/)

語言：[English](README.md) | [繁體中文](README.zh-TW.md)

`polars-baseball` 是 **The unified Polars-native baseball data SDK**：typed、async-first、
以 Polars 為核心的 Python 棒球資料擷取套件，統一存取 Statcast、Baseball Savant、
FanGraphs、Baseball Reference、Lahman、Retrosheet 與 MLB Stats API。

如果你正在找 `python baseball data`、`python statcast`、`fangraphs python`、
`baseball savant api`、`pybaseball alternative` 或 `polars dataframe baseball`，
這個專案服務的就是「資料直接進 `polars.DataFrame`，不要先繞過 pandas」的工作流。

## 為什麼不是只用 pybaseball？

`pybaseball` 很有用，也很成熟。`polars-baseball` 的定位不同：async ingestion、
原生 Polars 輸出，以及跨多個棒球資料來源的一致入口。

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

傳統 pandas-first 流程：

```text
pybaseball -> pandas -> convert to Polars -> analysis
```

`polars-baseball` 流程：

```text
polars-baseball -> Polars -> analysis
```

## 主要特性

- **Polars-native data**：公開資料擷取 API 會回傳 `polars.DataFrame`，除非 API 文件明確記載非表格 contract。
- **Async-first engine**：資料擷取 API 都是 `async def`，可以和既有 async workflow 組合。
- **多資料來源**：Statcast、Baseball Savant、FanGraphs、Baseball Reference、Lahman、
  Retrosheet、MLB Stats API 與 player ID workflow。
- **Built-in cache**：重複網路請求會以 Parquet 快取，適合大量查詢。
- **Service-ready context**：`BaseballContext` 讓長駐服務明確控制 HTTP 與 cache 資源。

## 安裝

```bash
pip install polars-baseball
```

本地開發：

```bash
git clone https://github.com/nicko4o/polars-baseball
cd polars-baseball
uv sync --all-extras
```

若要執行視覺化範例：

```bash
pip install "polars-baseball[plot]"
```

## 快速開始

### Statcast pitch-level data

```python
import asyncio

import polars_baseball as pb


async def main() -> None:
    df = await pb.statcast(start_date="2024-05-06", end_date="2024-05-06")
    print(df.head(5))


if __name__ == "__main__":
    asyncio.run(main())
```

### 直接用 Polars 聚合

```python
import asyncio

import polars as pl
import polars_baseball as pb


async def main() -> None:
    df = await pb.statcast_pitcher(
        start_date="2024-05-06",
        end_date="2024-05-06",
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

### FanGraphs 排行榜

```python
import asyncio

import polars_baseball as pb


async def main() -> None:
    df = await pb.fangraphs.batting(
        start_season=2024,
        end_season=2024,
        qual=100,
        max_results=20,
    )
    print(df.head(10))


if __name__ == "__main__":
    asyncio.run(main())
```

## Examples

可執行範例放在 [`examples/`](examples/)：

- [`examples/statcast_pitch_mix.py`](examples/statcast_pitch_mix.py)：Statcast pitch mix。
- [`examples/fangraphs_leaderboard.py`](examples/fangraphs_leaderboard.py)：FanGraphs batting leaderboard。
- [`examples/mlb_schedule.py`](examples/mlb_schedule.py)：MLB Stats API schedule query。
- [`examples/benchmark_statcast.py`](examples/benchmark_statcast.py)：保守的 Statcast timing 與 memory benchmark。

## Benchmark

先用可重現指令，不要相信沒有條件的效能口號：

```bash
python examples/benchmark_statcast.py --start-date 2024-04-01 --end-date 2024-04-07
```

腳本會輸出 rows、columns、wall time，以及 `tracemalloc` 量到的 Python allocation peak。
要比較 pandas-first workflow，請固定 date range、cache state、Python 版本與機器。

## Web 服務與高並行

未傳入 `context` 時，套件會使用隱式的 package-level `BaseballContext`。這對腳本很方便，
但長駐高並行服務應該自己管理 context，並把它傳給每次 API 呼叫。

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

## API 命名空間政策

套件根目錄（`import polars_baseball as pb`）公開核心 convenience API 與 provider namespace。
Provider-specific 工作流請使用 `pb.fangraphs`、`pb.savant`、`pb.mlb`。
Lahman、Retrosheet、Baseball Reference 與 player ID workflows 仍可從 package root 使用。

以 `_` 開頭的模組，包括 `_schemas`，都是內部實作細節，不屬於相容性承諾。

## 文件

- [Documentation](docs/index.md)
- [API 用途索引](docs/zh-tw/api_index.md)：依任務選擇正確 API。
- [繁體中文文件](docs/zh-tw/)

## Showcase

使用 `polars-baseball` 的專案：

- MLB dashboard workflows
- 中文棒球網站資料工作流
- Threads bot 棒球資料 pipeline

## 貢獻

開發流程與專案結構請參考 [CONTRIBUTING.zh-TW.md](.github/CONTRIBUTING.zh-TW.md)。

## 作者

由 Nick 建立與維護。
