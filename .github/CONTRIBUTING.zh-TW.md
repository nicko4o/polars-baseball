# 貢獻 polars-baseball

語言：[English](https://github.com/nicko4o/polars-baseball/blob/main/.github/CONTRIBUTING.md) | [繁體中文](https://github.com/nicko4o/polars-baseball/blob/main/.github/CONTRIBUTING.zh-TW.md)

歡迎提交 pull request 改進這個套件。為了維持程式品質與執行效能，所有貢獻都必須遵守明確的架構與工程紀律。

主要貢獻方向：
* 新增可信棒球資料來源的擷取支援，例如 FanGraphs、Baseball Reference 等。
* 修正既有 scraping、parsing 或資料契約錯誤。
* 改善文件、型別標註或測試。

---

## AI 協作貢獻政策 (AI-Assisted Contributions Policy)

我們歡迎使用 AI 工具（如 Copilot、ChatGPT、Claude 等）協助開發，但對「未經檢查的 AI 生成內容」採取零容忍態度：
* **完全負起責任**：你必須對所提交的每一行程式碼負 100% 的責任。你必須完全理解並能解釋 PR 中的所有邏輯。
* **嚴禁直接複製貼上**：請勿提交未經你親自執行、測試與審查的複製貼上程式碼。
* **拒絕幻覺內容**：凡是包含虛構庫 API (Hallucinated APIs) 或錯誤型別斷言的 PR，將會被直接關閉，不進行任何審查。

---

## 設計原則 (Design Principles)

我們的工程哲學偏好：
- **明確優於隱式 (Explicit over implicit)**：明確的參數與 context 優於神奇的假設。
- **可預測的 API 優於聰明的抽象 (Predictable APIs over clever abstractions)**：保持程式碼易讀且易於追蹤。
- **快速失敗優於靜默復原 (Fail fast over silent recovery)**：立即拋出診斷錯誤，而不是回傳半毀損的狀態。
- **穩定的 Schema 優於便利性 (Stable schemas over convenience)**：維持確定性的 DataFrame 結構。
- **組合優於繼承 (Composition over inheritance)**：保持輔助元件解耦且可互換。

---

## 指南與工程紀律

### 1. Polars 與 async-first 架構
* **Polars 優先**：公開資料 API 應預設回傳原生 `polars.DataFrame`（特別說明的例外如 `standings()` 除外）。禁止引入 Pandas。
* **Async 優先**：資料擷取 API 必須是非同步函式（`async def`），且支援自訂 `BaseballContext` 注入以實現資源隔離。
* **明確 Schema 契約**：每個回傳的 DataFrame 都必須在所屬解析器或 API 模組內，定義明確的 Polars schema contract（例如 `BWAR_BAT_SCHEMA`）。
* **公開匯出契約**：新增的公開 entry points 必須宣告在 `polars_baseball.__all__` 中，並由 API contract tests 覆蓋。

### 2. 型別安全與程式碼品質
* **型別標註**：只要更精確的型別是可行的，應避免使用 `Any` 或弱型別。若必須使用 `Any`（例如在 fallback 解析或 JSON 結構中），必須說明原因。
* **MyPy 檢查**：程式碼必須通過嚴格型別檢查 (`uv run mypy polars_baseball/`)，且不得有任何錯誤。
* **禁止 Magic 常數**：避免在業務邏輯中嵌入未命名的數字或字串。將常數集中定義於 enum 或設定中。
* **函式長度**：偏好小而高內聚的函式。當函式增長超過大約 50 LOC 時，考慮拆分出較小的輔助函式。
* **Fail Fast**：撰寫防禦性程式碼。避免吞掉例外或在格式異常時靜默復原。

### 3. 快取與 Docstring 語意
* **快取語意**：如果 API 讀取、寫入、分片或繞過快取，必須記錄其快取行為（包含快取位置、快取金鑰生成方式、TTL 與強制重新整理機制）。
* **Docstring 指南**：Public API docstrings 應僅記錄無法直接從函式簽章或型別提示中推導出的行為。不要重複 type hints。著重於：
  - 可觀察的副作用（如網路請求、快取寫入）。
  - 行為契約。
  - 相容性或非直覺的 edge cases。

---

## 專案配置 (Project Layout)

- `polars_baseball/apis/`：穩定且面向使用者公開的 API 端點。
- `polars_baseball/gateways/`：網路邊界、外部 HTTP 用戶端設定與資料擷取層。
- `polars_baseball/parsers/`：純解析器，採用策略模式轉換原始資料。
- `polars_baseball/schemas/`：宣告式 schema 結構與驗證契約。
- `polars_baseball/enums/`：集中定義的領域相關 enum 與常數表。
- `polars_baseball/data/`：靜態參考資料集（如球隊 ID 映射表）。

---

## 測試哲學 (Testing Philosophy)

- **偏好單元測試**：使用 `tests/polars_baseball/data/` 的 mock 輸入，在離線狀態下驗證解析與業務邏輯。
- **避免網路請求**：預設情況下測試絕對不能發送網路請求至真實伺服器。
- **標記 Live 測試**：需要網際網路連線的測試必須標記 `@pytest.mark.live`，且在一般 CI 流程中會被跳過。

---

## 開發流程

### 1. 本地設定
本專案使用 `uv` 管理依賴，確保安裝快速且可重現。

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

* **格式化與 lint**：
  ```bash
  uv run ruff check polars_baseball/ --fix
  uv run ruff format polars_baseball/
  ```
* **MyPy 型別檢查**：
  ```bash
  uv run mypy polars_baseball/
  # Or via Makefile:
  make mypy ONLY_MODIFIED=0
  ```
* **測試**：
  ```bash
  uv run pytest tests/polars_baseball -m "not live"
  # Or via Makefile:
  make test TEST_FLAGS='-n auto -m "not live"'
  ```

### 3. Commit message 與 Git 紀律
本專案強制使用 **Conventional Commits**。
* 使用 `feat:`、`fix:`、`docs:`、`refactor:`、`test:` 或 `ci:` 等 prefix。
* 範例：`git commit -m "feat: add expected stats parser for statcast"`
* **Release 提交**：僅在正式發布新版本時，才允許提交以 `release: vX.Y.Z` 或 `chore(release): vX.Y.Z` 開頭的 commit。
* 範例：`release: v0.1.0 initial release of polars-baseball`

---

## 提交 Pull Request

### 1. 分支策略 (Branch Policy)
* 從 `main` 分支建立 feature 或 bugfix 分支。
* 向 `main` 分支發起 Pull Request。
* 所有併入 `main` 的 PR 必須透過 **Squash and Merge**（壓縮合併）進行合併，以保持主分支歷史乾淨。
* 直接提交（Direct Commit）或非壓縮合併至 `main` 的權利，僅保留給正式的 release commit（需附帶 `vX.Y.Z` tag）。

### 2. 一般範圍 (General Scope)
* 保持 PR 範圍高度聚焦，請勿將無關的重構與功能開發混在一起。
* 確保新功能均有 `tests/polars_baseball/` 下的單元測試覆蓋。
* 若 API 簽章或行為有變更，必須同步更新 `docs/` 下的文件。請遵守 `docs/MAINTAINING.md`，把內容放到正確層級，不要新增重複頁面。

### 3. 超出範圍的貢獻 (Out-of-Scope Contributions)
以下變更通常不屬於專案接受的範圍，在嘗試前請先開 Issue 或進行討論：
- 僅進行程式碼格式調整的 PR（本專案在每次建置/CI 時皆會執行自動格式化）。
- 在開發新功能時，順便在其他模組進行的大型且無關的重構。
- 未經維護者事先同意，引入新的第三方套件依賴。
- 在沒有事先設計遷移路徑的情況下，提交破壞性的 API 結構變更。
