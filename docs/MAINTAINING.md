# Documentation Maintenance Rules

This project keeps documentation intentionally small and layered. Do not add a new page until one of these existing layers cannot carry the information.

## Layers

| Layer | Purpose | Update when |
| --- | --- | --- |
| `README.md` / `README.zh-TW.md` | Project positioning, install, quick start, and two documentation entry points. | Installation, quick start, or project positioning changes. |
| `docs/index.md` | Documentation table of contents. | A document is added, removed, or moved. |
| `docs/api_index.md` | Task-to-API chooser. | A public API adds a new user-visible use case. |
| `docs/guides/` | Workflows and operational usage. | A workflow changes, such as caching, notebooks, plotting, or service usage. |
| `docs/reference/` | Public API contracts by provider or domain. | Function signature, return contract, parameter semantics, edge cases, or source behavior changes. |

## Rules

- README must not contain the full documentation tree.
- `docs/internal/` is reserved for maintainer-only architecture notes. Public API usage belongs in `docs/reference/`.
- Do not duplicate type hints in prose unless the type alone does not explain allowed values or units.
- Prefer updating an existing provider reference page over creating a one-function page.
- Remove stale content instead of preserving historical behavior in reference docs. Historical behavior belongs in the changelog.
- Every public data-fetching API example must be executable Python, not pseudo-code.

# 文件維護規則

本專案的文件刻意維持精簡與分層。新增頁面前，必須先確認既有層級無法承載該資訊。

## 層級

| 層級 | 責任 | 何時更新 |
| --- | --- | --- |
| `README.md` / `README.zh-TW.md` | 專案定位、安裝、快速開始，以及少量文件入口。 | 安裝方式、快速開始或專案定位改變時。 |
| `docs/index.md` | 文件目錄。 | 文件新增、刪除或搬移時。 |
| `docs/api_index.md` | 依任務選 API 的索引。 | Public API 新增使用者可見的使用情境時。 |
| `docs/guides/` | 工作流與操作指南。 | 快取、Notebook、繪圖或服務使用方式等工作流改變時。 |
| `docs/reference/` | 依 provider 或 domain 分組的 public API contract。 | 函式簽章、回傳 contract、參數語意、edge cases 或資料來源行為改變時。 |

## 規則

- README 不得包含完整文件樹。
- `docs/internal/` 只保留維護者專用架構筆記。Public API 使用方式必須放在 `docs/reference/`。
- 不要在 prose 重複 type hints，除非型別本身無法解釋允許值或單位。
- 優先更新既有 provider reference 頁，不要為單一函式新增頁面。
- 過期內容要刪除，不要保留在 reference docs。歷史行為應放在 changelog。
- 每個 public data-fetching API 範例都必須是可執行 Python，不准寫 pseudo-code。
