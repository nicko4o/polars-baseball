> [!NOTE]
> 所有公開資料擷取 API 都是非同步函式。請在 async 環境中使用 `await`，或在指令碼中用 `asyncio.run()` 包裝呼叫。

# Baseball Reference

提供從 Baseball Reference 擷取每日 WAR（Wins Above Replacement，勝場貢獻值）與歷史統計數據的函式。

---

## 速率限制與 Cloudflare

> [!WARNING]
> Baseball Reference 執行嚴格的速率限制：**每分鐘最多 10 次請求**。超出此限制會傳回 HTTP 429 回應。
> 此外，部分端點受到 Cloudflare Turnstile 安全機制保護。在線上環境驗證中，Baseball Reference 可能會傳回 HTTP 403 Forbidden 錯誤，因此本頁面特意省略保證非空的執行範例。

---

## 打擊 WAR (Batting WAR)

從 `war_daily_bat` 資料庫表中擷取 Baseball Reference 每日打擊 WAR 資料。

### 函式

- `bwar_bat(return_all: bool = False) -> pl.DataFrame`

### 參數

- `return_all`：當為 `True` 時，傳回 `war_daily_bat` 表中的所有可用欄位；當為 `False` 時，傳回資料分析工作流中常用的標準欄位子集。

---

## 投球 WAR (Pitching WAR)

從 `war_daily_pitch` 資料庫表中擷取 Baseball Reference 每日投球 WAR 資料。

### 函式

- `bwar_pitch(return_all: bool = False) -> pl.DataFrame`

### 參數

- `return_all`：當為 `True` 時，傳回 `war_daily_pitch` 表中的所有可用欄位；當為 `False` 時，傳回資料分析工作流中常用的標準欄位子集。

---

## 範例

```python
import asyncio
from polars_baseball import bwar_bat, bwar_pitch

async def main() -> None:
    # 擷取標準每日打擊 WAR（在線上測試環境中可能會引發 HTTP 403）
    try:
        batting_war = await bwar_bat(return_all=False)
        print("Batting WAR:", batting_war.head())
    except Exception as e:
        print("Could not retrieve Batting WAR:", e)

    # 擷取標準每日投球 WAR
    try:
        pitching_war = await bwar_pitch(return_all=False)
        print("Pitching WAR:", pitching_war.head())
    except Exception as e:
        print("Could not retrieve Pitching WAR:", e)

if __name__ == "__main__":
    asyncio.run(main())
```
