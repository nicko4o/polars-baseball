# polars-baseball

語言：[English](README.md) | [繁體中文](README.zh-TW.md)

`polars-baseball` 是以 **Polars** 為核心、非同步優先的 Python 棒球資料擷取套件。公開資料 API 以 `async def` 提供，多數公開資料 API 回傳原生 `polars.DataFrame`（特別說明的例外如 `standings()` 則回傳其他格式），適合 Statcast、Baseball Reference、FanGraphs、Lahman、Retrosheet 與球員 ID 查詢工作流。

---

## 主要特性

- **Polars Core**：多數公開 API 回傳原生 `polars.DataFrame`（例外如 `standings()` 回傳 `list[polars.DataFrame]`），方便直接使用 Polars expression 做篩選、聚合與輸出。
- **Async-First Engine**：資料擷取 API 皆為非同步函式，需在 async 環境中使用 `await`，或在指令碼內用 `asyncio.run()` 執行。
- **彈性並行**：支援自訂 context 設定以在多執行緒或多事件循環環境中隔離連線資源。
- **Automatic Cache**：內建檔案快取，Statcast 與 Lahman 等大量查詢可減少重複網路請求。

---

## 安裝

```bash
pip install polars-baseball
```

若要本地開發：

```bash
git clone https://github.com/nicko4o/polars-baseball
cd polars-baseball
uv sync --all-extras
```

若要執行文件中的視覺化範例，可安裝選用範例依賴：

```bash
pip install "polars-baseball[plot]"
```

---

## 快速開始

### 1. Statcast 查詢

```python
import asyncio

import polars_baseball as pb


async def main() -> None:
    df = await pb.statcast(start_dt="2024-05-06", end_dt="2024-05-06")
    print(df.head(5))

    darvish_df = await pb.statcast_pitcher(
        start_dt="2024-05-06",
        end_dt="2024-05-06",
        player_id=450314,
    )
    print(darvish_df.head(5))


if __name__ == "__main__":
    asyncio.run(main())
```

### 2. 使用 Polars 聚合資料

```python
import asyncio

import polars as pl
import polars_baseball as pb


async def main() -> None:
    darvish_df = await pb.statcast_pitcher(
        start_dt="2024-05-06",
        end_dt="2024-05-06",
        player_id=450314,
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

### 4. 互動式資料視覺化

`polars-baseball` 不提供繪圖 API。這個範例只是把回傳的 `polars.DataFrame` 交給 hvPlot。

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

## Web 服務與高並行 (FastAPI, Gunicorn, Celery)

預設情況下，呼叫套件函式而不傳入 context 參數時，將會 fallback 回隱式的套件級全域單例 `BaseballContext`。**此全域預設 context 在長駐的高並行環境中，不保證執行緒安全（thread-safe）或事件循環安全（loop-safe）。**

當在並行 Web 服務（如 FastAPI、Gunicorn 或 Celery worker）中部署 `polars-baseball` 時，您**必須**顯式管理 `BaseballContext` 的生命週期，並將其傳入所有 API 呼叫中。

### FastAPI lifespan 範例

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI
import polars_baseball as pb

@asynccontextmanager
async def lifespan(app: FastAPI):
    # 初始化一個與 app 事件循環繫結的專屬 context
    app.state.pb_context = pb.BaseballContext()
    try:
        yield
    finally:
        # 正確關閉 HTTP 連線以防資源洩漏
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

## API 命名空間政策

套件根目錄（`import polars_baseball as pb`）只公開穩定且常用的 public API。Provider-specific 與進階函式保留在 `polars_baseball.apis.*`。

以 `_` 開頭的模組，包括 `_schemas`，都是內部實作細節，不屬於相容性承諾。

---

## 文件

- [繁體中文文件](docs/zh-tw/)
- [English documentation](docs/)
- [快取指南](docs/zh-tw/caching.md)
- [資料視覺化指南](docs/zh-tw/plotting.md)
- [Statcast API](docs/zh-tw/statcast.md)
- [Player ID Lookup](docs/zh-tw/playerid_lookup.md)
- [MLB Stats API](docs/zh-tw/mlb_api.md)
- [Savant Gamefeed API](docs/zh-tw/savant_gamefeed.md)
- [Prospect Rankings](docs/zh-tw/prospect_rankings.md)

---

## 貢獻

開發流程與專案結構請參考 [CONTRIBUTING.zh-TW.md](.github/CONTRIBUTING.zh-TW.md)。

---

## 作者

由 Nick 建立與維護。
