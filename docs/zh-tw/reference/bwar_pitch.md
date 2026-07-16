> [!NOTE]
> 所有公開資料擷取 API 都是非同步函式。請在 async 環境中使用 `await`，或在指令碼中用 `asyncio.run()` 包裝呼叫。

# Baseball Reference 投球 WAR

`bwar_pitch(return_all: bool = False) -> pl.DataFrame`

從 Baseball Reference 的 `war_daily_pitch` 表查詢 投球 WAR 資料。

## 參數

- `return_all`：`True` 時回傳 `war_daily_pitch` 的所有欄位；`False` 時回傳常用工作流需要的標準欄位子集。

## Live-data 限制

Baseball Reference 目前在 live 驗證中對此 endpoint 回傳 HTTP 403，因此本頁刻意不提供「保證非空」的可執行範例。
