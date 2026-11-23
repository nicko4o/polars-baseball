# polars-baseball

[![PyPI version](https://img.shields.io/pypi/v/polars-baseball.svg)](https://pypi.org/project/polars-baseball/)
[![Python versions](https://img.shields.io/pypi/pyversions/polars-baseball.svg)](https://pypi.org/project/polars-baseball/)
[![CI](https://github.com/nicko4o/polars-baseball/actions/workflows/pytest.yml/badge.svg)](https://github.com/nicko4o/polars-baseball/actions)
[![Codecov](https://img.shields.io/codecov/c/github/nicko4o/polars-baseball)](https://codecov.io/gh/nicko4o/polars-baseball)
[![License](https://img.shields.io/pypi/l/polars-baseball.svg)](https://github.com/nicko4o/polars-baseball/blob/main/LICENSE)
[![Downloads](https://img.shields.io/pypi/dm/polars-baseball.svg)](https://pypi.org/project/polars-baseball/)

語言：[English](README.md) | [繁體中文](README.zh-TW.md)

`polars-baseball` 是以 Polars 為核心、支援非同步（async-first）且具備完整型別標註的 Python 棒球資料擷取套件，直接將 Statcast、Baseball Savant、FanGraphs、Baseball Reference、Lahman、Retrosheet 與 MLB Stats API 資料轉為 `polars.DataFrame`，省去先經過 pandas 轉換的步驟。

## 核心設計

所有公開資料擷取 API 皆為 `async def`，預設回傳 `polars.DataFrame`（特定端點如 `bref.splits()` 或 `savant.scan_statcast()` 則回傳文件記載之對應型別）。透過 `BaseballClient` 可集中管理 HTTP 連線池、重試次數、請求頻率限制（`HttpClient`）以及本地 Parquet 快取，統一存取 7 大資料源（`savant`、`fangraphs`、`bref`、`mlb`、`retrosheet`、`lahman`、`lookup`）。

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

## 快速開始

```python
import asyncio
import polars as pl
from polars_baseball import BaseballClient


async def main() -> None:
    async with BaseballClient() as client:
        df = await client.savant.pitcher(
            start_date="2026-06-01",
            end_date="2026-06-01",
            # 不知道 ID 可用 await client.lookup.playerid_lookup("Judge", "Aaron") 查詢
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

可執行範例放在 [`examples/`](examples/)，互動式 Jupyter notebooks 放在 [`notebooks/`](notebooks/)：

- [`examples/statcast_pitch_mix.py`](examples/statcast_pitch_mix.py) / [`notebooks/statcast_pitch_mix_demo.ipynb`](notebooks/statcast_pitch_mix_demo.ipynb)
- [`examples/fangraphs_leaderboard.py`](examples/fangraphs_leaderboard.py) / [`notebooks/fangraphs_leaderboard_demo.ipynb`](notebooks/fangraphs_leaderboard_demo.ipynb)
- [`examples/mlb_schedule.py`](examples/mlb_schedule.py) / [`notebooks/mlb_schedule_demo.ipynb`](notebooks/mlb_schedule_demo.ipynb)

## Web 服務與高並行

長駐服務應在應用程式生命週期內共用單一 `BaseballClient`：

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

## 效能基準測試 (Benchmark)

```bash
python -m benchmarks run list
python -m benchmarks run statcast_7day_cold [--baseline] [--fail-if-regression]
```

## 文件與專案治理

- [文件首頁與 API 索引](docs/index.md)
- [維護者指南](docs/MAINTAINING.md)
- [貢獻指南](.github/CONTRIBUTING.md) · [資安漏洞通報政策](.github/SECURITY.md)

## 資料來源聲明與防爬蟲限制

`polars-baseball` 不主張任何上游資料來源之所有權：

- Retrosheet：The information used here was obtained free of charge from and is copyrighted by Retrosheet（[www.retrosheet.org](https://www.retrosheet.org)）。
- Statcast 與 MLB Stats API 資料由 Major League Baseball / Baseball Savant 提供。
- FanGraphs 與 Baseball Reference 仰賴網頁擷取且受 Cloudflare Turnstile 與嚴格頻率限制保護，存取屬於盡力而為（Best-Effort）。請設定合理的 `bref_requests_per_minute`、於受挑戰時藉由 `extra_headers` 傳入 `CF_CLEARANCE` / `CF_COOKIE`，或善用本地 Parquet 快取。
- Lahman 資料集為 Sean Lahman 維護之 Lahman's Baseball Database。

## 引用與授權

學術或專案引用請參考 [`CITATION.cff`](CITATION.cff)。本專案由 Nick 建立與維護，採用 [MIT License](LICENSE) 授權。
