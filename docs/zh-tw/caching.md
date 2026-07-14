# 快取指南

`polars-baseball` 內建檔案快取，可降低大量資料查詢時的重複網路請求。

## 快取策略

- **預設狀態**：快取預設啟用。
- **儲存位置**：未另行設定時，快取資料會存放在 `~/.polars_baseball/cache`。
- **儲存格式**：快取表格使用 Parquet，以取得較快 I/O 與欄式壓縮。

## 設定快取位置

### 程式內設定

使用 `polars_baseball` 的 `configure_cache`：

```python
from pathlib import Path
from polars_baseball import configure_cache

custom_cache_path = Path("./my_project_cache")
configure_cache(custom_cache_path)
```

長時間執行的指令碼如果需要明確關閉套件層級 HTTP client，可以呼叫 `cleanup`：

```python
import asyncio
from polars_baseball import cleanup

async def main() -> None:
    await cleanup()

if __name__ == "__main__":
    asyncio.run(main())
```

### 長駐服務與高並行生命週期

全域預設 context（在呼叫 API 時不傳入 `context=` 時使用）是為 CLI 指令碼設計的延遲載入單例（lazy singleton）。在長駐的高並行應用程式中（如 FastAPI 或 Celery），它**不是**執行緒安全或事件循環安全的。

對於 Web 服務，請務必初始化並注入與應用程式生命週期繫結的自訂 `BaseballContext`：

```python
from fastapi import FastAPI
from polars_baseball import BaseballContext

# 與 lifespan 繫結
async def lifespan(app: FastAPI):
    app.state.pb_context = BaseballContext()
    try:
        yield
    finally:
        await app.state.pb_context.http.close()
```

### 環境變數

```bash
export POLARS_BASEBALL_CACHE_DIR="/path/to/your/custom/cache"
```

## 快取行為

- **參數層級匹配**：快取鍵由函式與完整參數組成。完全相同的呼叫會重用快取。
- **不做子區間匹配**：`statcast("2024-05-01", "2024-05-10")` 的快取不會被 `statcast("2024-05-05", "2024-05-06")` 重用。
- **Lahman database**：下載的 Lahman 壓縮檔與解出的表格會存放在同一個快取目錄。
