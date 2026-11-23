# 貢獻 polars-baseball

語言：[English](https://github.com/nicko4o/polars-baseball/blob/main/.github/CONTRIBUTING.md) | [繁體中文](https://github.com/nicko4o/polars-baseball/blob/main/.github/CONTRIBUTING.zh-TW.md)

歡迎提交 pull request 改進這個套件。為了維持程式品質與執行效能，所有貢獻都必須遵守明確的架構與工程紀律。主要貢獻方向包含新增可信棒球資料來源（如 FanGraphs、Baseball Reference 等）的擷取支援、修正既有的爬取或解析契約錯誤，以及改善文件、型別標註或測試。

---

## AI 協作貢獻政策 (AI-Assisted Contributions Policy)

我們歡迎使用 AI 工具（如 Copilot、ChatGPT、Claude 等）協助開發，但對未經檢查的 AI 生成內容採取零容忍態度。

你必須對所提交的每一行程式碼負 100% 責任，完全理解並能解釋 PR 中的所有邏輯。請勿直接複製貼上未經親自執行、測試與審查的程式碼；凡包含虛構庫 API (Hallucinated APIs) 或錯誤型別斷言的 PR，將會直接關閉而不予審查。

---

## 設計原則 (Design Principles)

我們的工程哲學偏好以下原則：

- 明確優於隱式 (Explicit over implicit)：使用明確參數與 context，避免隱藏假設。
- 可預測的 API 優於聰明的抽象 (Predictable APIs over clever abstractions)：保持程式碼易讀且易於追蹤。
- 快速失敗優於靜默復原 (Fail fast over silent recovery)：立即丟出診斷錯誤，而不是回傳半毀損的狀態。
- 穩定的 Schema 優於便利性 (Stable schemas over convenience)：維持確定性的 DataFrame 結構。
- 組合優於繼承 (Composition over inheritance)：保持輔助元件解耦且可互換。

---

## 指南與工程紀律

### 1. Polars 與 async-first 架構

公開資料 API 應預設回傳原生 `polars.DataFrame`（特別說明的例外如回傳 `list[pl.DataFrame]` 的 `bref.splits()` 或回傳 `pl.LazyFrame` 的 `savant.scan_statcast()` 除外），且禁止引入 Pandas。所有資料擷取 API 都必須是非同步函式（`async def`），並藉由 `BaseballClient` 子命名空間存取以實現資源隔離。

每個回傳的 DataFrame 都必須在所屬解析器或 schema 模組內定義明確的 Polars schema contract（例如 `BWAR_BAT_SCHEMA`）；新增的公開 entry points 也必須宣告在 `polars_baseball.__all__` 中，並由 API contract tests 覆蓋。

### 2. 型別安全與程式碼品質

只要更精確的型別可行，應避免使用 `Any` 或弱型別；若在 fallback 解析或 JSON 結構中必須使用 `Any`，請註明原因。程式碼必須能過嚴格型別檢查（`uv run mypy polars_baseball/`），不得有任何錯誤。

業務邏輯中禁止嵌入未命名的 magic numbers 或字串，請集中定義於 enum 或設定檔。函式應保持小而高內聚，超過約 50 LOC 時考慮拆出較小的輔助函式，並以防禦性程式碼落實 fail fast，避免吞掉例外或靜默復原。

### 3. 快取與 Docstring 語意

如果 API 會讀取、寫入、分片或繞過快取，必須記錄其快取行為（包含快取位置、快取金鑰生成方式、TTL 與強制重新整理機制）。Public API docstrings 僅需記錄無法從簽章或型別推導出的行為，不要重複 type hints，並聚焦於可觀察副作用（網路請求、快取寫入）、行為契約與非直覺的 edge cases。

---

## 專案配置 (Project Layout)

- `polars_baseball/client.py`：主要客戶端入口點（`BaseballClient`）。
- `polars_baseball/gateways/`：網路邊界、外部 HTTP 用戶端設定與資料擷取層。
- `polars_baseball/parsers/`：純解析器，採用策略模式轉換原始資料。
- `polars_baseball/_schemas/`：宣告式 schema 結構與驗證契約。
- `polars_baseball/_mlb/`：解構之 MLB 領域 mixins。
- `polars_baseball/_savant/`：解構之 Savant 領域 mixins。
- `polars_baseball/enums/`：集中定義的領域相關 enum 與常數表。
- `polars_baseball/data/`：靜態參考資料集（如球隊 ID 映射表）。

---

## 測試哲學 (Testing Philosophy)

單元測試應使用 `tests/polars_baseball/data/` 的 mock 輸入，在離線狀態下驗證解析與業務邏輯；預設測試不得傳送網路請求至真實伺服器。需要連線的測試必須標記 `@pytest.mark.live`，一般 CI 流程會略過這些測試。

---

## 開發流程

### 1. 本地設定

本專案使用 `uv` 管理相依性，確保安裝快速且可重現：

```bash
# Fork and clone the repository
git clone git@github.com:<your GitHub handle>/polars-baseball.git
cd polars-baseball
git remote add upstream git@github.com:nicko4o/polars-baseball.git

# Initialize environment and install in editable mode with test dependencies
uv sync --all-extras
```

### 2. 本地驗證

提交 pull request 前，必須依序執行以下檢查。

格式化與 lint：

```bash
uv run ruff check polars_baseball/ --fix
uv run ruff format polars_baseball/
```

MyPy 型別檢查：

```bash
uv run mypy polars_baseball/
# Or via Makefile:
make mypy ONLY_MODIFIED=0
```

測試：

```bash
uv run pytest tests/polars_baseball -m "not live"
# Or via Makefile:
make test TEST_FLAGS='-n auto -m "not live"'
```

### 3. Commit message 與 Git 紀律

本專案強制使用 Conventional Commits，請使用 `feat:`、`fix:`、`docs:`、`refactor:`、`test:` 或 `ci:` 等 prefix（例如 `git commit -m "feat: add expected stats parser for statcast"`）。僅在正式發布新版本時，才允許提交以 `release: vX.Y.Z` 或 `chore(release): vX.Y.Z` 開頭的 commit。

---

## 提交 Pull Request

### 1. 分支策略 (Branch Policy)

請從 `main` 分支建立 feature 或 bugfix 分支，並向 `main` 發起 Pull Request。所有併入 `main` 的 PR 都會採用 Squash and Merge（壓縮合併）以保持主分支歷史乾淨；直接提交或非壓縮合併至 `main` 僅保留給附帶 `vX.Y.Z` tag 的正式 release commit。

### 2. 一般範圍 (General Scope)

保持 PR 範圍高度聚焦，不要將無關的重構與功能開發混在一起，並確保新功能有 `tests/polars_baseball/` 下的單元測試覆蓋。若 API 簽章或行為有變更，必須同步更新 `docs/` 下的文件，並遵守 `docs/MAINTAINING.md` 將內容放到正確層級。

### 3. 超出範圍的貢獻 (Out-of-Scope Contributions)

僅進行程式碼格式調整的 PR（CI 建置時會自動格式化）、開發新功能時順便進行的跨模組大型重構、未經同意引入新的第三方相依性，以及沒有遷移路徑的破壞性 API 變更，通常不屬於專案接受範圍，嘗試前請先開 Issue 討論。
