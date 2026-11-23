# polars-baseball

[![PyPI version](https://img.shields.io/pypi/v/polars-baseball.svg)](https://pypi.org/project/polars-baseball/)
[![Python versions](https://img.shields.io/pypi/pyversions/polars-baseball.svg)](https://pypi.org/project/polars-baseball/)
[![CI](https://github.com/nicko4o/polars-baseball/actions/workflows/pytest.yml/badge.svg)](https://github.com/nicko4o/polars-baseball/actions)
[![Codecov](https://img.shields.io/codecov/c/github/nicko4o/polars-baseball)](https://codecov.io/gh/nicko4o/polars-baseball)
[![License](https://img.shields.io/pypi/l/polars-baseball.svg)](https://github.com/nicko4o/polars-baseball/blob/main/LICENSE)
[![Downloads](https://img.shields.io/pypi/dm/polars-baseball.svg)](https://pypi.org/project/polars-baseball/)

語言：[English](README.md) | [繁體中文](README.zh-TW.md)

`polars-baseball` 是以 Polars 為核心、支援非同步（async-first）且具備完整型別標註的 Python 棒球資料擷取套件，統一存取 Statcast、Baseball Savant、FanGraphs、Baseball Reference、Lahman、Retrosheet 與 MLB Stats API，讓資料直接進到 `polars.DataFrame`，不必先經過 pandas 轉換。

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

- 公開資料擷取 API 預設回傳 `polars.DataFrame`（除非該端點明確記載為非表格資料）。
- 所有資料擷取 API 皆為 `async def`，可直接與現有的 `asyncio` 非同步流程組合。
- 統一存取 Statcast、Baseball Savant、FanGraphs、Baseball Reference、Lahman、Retrosheet、MLB Stats API 與球員 ID 查詢。
- 內建可選的本地 Parquet 快取，減少大量查詢時的重複網路請求。
- 藉由 `BaseballClient` 讓長駐服務明確管理 HTTP 連線池與快取生命週期。
- `HttpClient` 提供逾時時間、重試次數與 Baseball Reference 請求頻率限制設定。

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

from polars_baseball import BaseballClient


async def main() -> None:
    async with BaseballClient() as client:
        df = await client.savant.statcast(start_date="2026-06-01", end_date="2026-06-01")
        print(df.head(5))


if __name__ == "__main__":
    asyncio.run(main())
```

### 直接用 Polars 聚合

```python
import polars as pl
from polars_baseball import BaseballClient

async with BaseballClient() as client:
    df = await client.savant.pitcher(
        start_date="2026-06-01",
        end_date="2026-06-01",
        # 不知道 ID？用 await client.lookup.playerid_lookup("Judge", "Aaron") 查詢
        player_id=506433,
    )
    summary = df.group_by("pitch_type").agg(
        pl.col("release_speed").mean().alias("mean_speed"),
        pl.len().alias("pitch_count"),
    )
    print(summary.sort("pitch_count", descending=True))
```

### FanGraphs 排行榜

```python
from polars_baseball import BaseballClient

async with BaseballClient() as client:
    df = await client.fangraphs.batting(
        start_season=2026,
        end_season=2026,
        qual=100,
        max_results=20,
    )
    print(df.head(10))
```

## 範例

### 腳本（CLI-ready）

可執行 `.py` 範例放在 [`examples/`](examples/)：

- [`examples/statcast_pitch_mix.py`](examples/statcast_pitch_mix.py)：Statcast pitch mix。
- [`examples/fangraphs_leaderboard.py`](examples/fangraphs_leaderboard.py)：FanGraphs batting leaderboard。
- [`examples/mlb_schedule.py`](examples/mlb_schedule.py)：MLB Stats API schedule query。

### Notebooks（互動式）

可互動執行的 Jupyter notebook 放在 [`notebooks/`](notebooks/)：

- [`notebooks/statcast_pitch_mix_demo.ipynb`](notebooks/statcast_pitch_mix_demo.ipynb)：Statcast pitch mix、球速排行、擊球結果。
- [`notebooks/fangraphs_leaderboard_demo.ipynb`](notebooks/fangraphs_leaderboard_demo.ipynb)：FanGraphs 打擊排行榜與 sabermetric 篩選。
- [`notebooks/mlb_schedule_demo.ipynb`](notebooks/mlb_schedule_demo.ipynb)：MLB 賽程、戰績、名單與球隊資料。
## 效能基準測試 (Benchmark)

先用可重現指令，不要相信沒有條件的效能口號：

```bash
python -m benchmarks run statcast_7day_cold
```

列出可用 profiles：

```bash
python -m benchmarks run list
```

完整指令：

```text
python -m benchmarks run <profile> [--json] [--json-file PATH] [--baseline] [--fail-if-regression]
python -m benchmarks baseline show
python -m benchmarks baseline clear
```

Runner 會回報 wall time、CPU time、peak Python memory（使用 `tracemalloc` 測量）、GC collections
以及 result shape。加上 `--baseline` 旗標可儲存結果並與歷史資料比對。
若要比較 pandas-first 工作流，請固定日期範圍、快取狀態、Python 版本與測試機器。

## Web 服務與高並行

長駐高並行服務應該自己管理 `BaseballClient`，並把它傳給每次 API 呼叫，達到明確連線池與資源管理：

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
    df = await client.savant.statcast(
        start_date="2026-06-01",
        end_date="2026-06-02",
    )
    return {"rows": df.height}
```

## API 命名空間政策

套件根目錄（`import polars_baseball as pb`）公開 7 大 Provider 命名空間（`pb.savant`、`pb.fangraphs`、`pb.bref`、`pb.mlb`、`pb.retrosheet`、`pb.lahman`、`pb.lookup`）、Client 類別（`pb.BaseballClient`）與核心 Enum（`Position`、`KeyType`）。

各資料源專屬函式與 Enum 均收斂於各自命名空間中（例如 `pb.fangraphs.*`、`pb.mlb.*`）。以 `_` 開頭的模組，包括 `_schemas`，都是內部實作細節，不屬於相容性承諾。

## 文件與資源

- [文件首頁 (Documentation Home)](docs/index.md)：使用指南、Notebooks 與各資料源 API 參考。
- [API 用途索引 (API Index)](docs/api_index.md)：依任務選擇正確 API。
- [維護者指南 (Maintaining Guide)](docs/MAINTAINING.md)：套件發布與維護流程。

## 社群規範與專案治理

我們非常歡迎社群貢獻！在提交 Pull Request 或 Issue 前，請閱讀相關規範：

- [開發與貢獻指南](.github/CONTRIBUTING.zh-TW.md) (包含 AI 輔助程式碼提交規範)
- [行為準則](.github/CODE_OF_CONDUCT.zh-TW.md)
- [資安漏洞通報政策](.github/SECURITY.zh-TW.md)

## 資料來源聲明與版權 (Data Attribution & Copyright Notices)

`polars-baseball` 為資料擷取 SDK，並不主張任何上游資料來源之所有權：

- Retrosheet：The information used here was obtained free of charge from and is copyrighted by Retrosheet. Interested parties may contact Retrosheet at [www.retrosheet.org](https://www.retrosheet.org).
- Statcast 與 MLB Stats API 資料由 Major League Baseball / Baseball Savant 提供。
- FanGraphs 與 Baseball Reference 資料由各自平台授權提供，請遵循上游服務條款與請求頻率限制。
- Lahman 資料集為 Sean Lahman 維護之 Lahman's Baseball Database。

> [!IMPORTANT]
> **FanGraphs 與 Baseball Reference「盡力而為（Best-Effort）」與防爬蟲聲明**：
> 有別於官方或封裝歸檔來源（MLB Stats API、Savant、Retrosheet、Lahman），FanGraphs 與 Baseball Reference 仰賴網頁擷取（Web Scraping），且受 Cloudflare Turnstile 與嚴格頻率限制保護。存取此二來源屬於**盡力而為（Best-Effort）**。請設定合理的請求頻率（`bref_requests_per_minute`）、於受挑戰時藉由 `extra_headers` 傳入通行 Cookie（`CF_CLEARANCE`, `CF_COOKIE`），或善用本地 Parquet 快取。

## 學術與研究引用 (Citation)

若你在學術研究、棒球分析論文或軟體專案中使用 `polars-baseball`，請參考 [`CITATION.cff`](CITATION.cff) 進行引用。

## 作者

由 Nick 建立與維護。

## 授權條款

本專案採用 [MIT License](LICENSE) 授權。

