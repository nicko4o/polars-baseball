# Documentation Maintenance Rules

Keep documentation layered and minimal. Source signatures and type annotations are the single source of truth—reference pages use `mkdocstrings` instead of duplicating signatures in prose.

## Layers

| Layer | Purpose | Update when |
| --- | --- | --- |
| `README.md` / `README.zh-TW.md` | Positioning, install, quick start, and docs link. | Install or quick start changes. |
| `docs/index.md` | Table of contents and task-to-API index. | Pages or major use cases change. |
| `docs/guides/` | Cross-cutting operational workflows (caching, errors). | Operational behavior changes. |
| `docs/reference/` | Provider caveats, edge cases, and `mkdocstrings` API refs. | Provider quirks or non-obvious behavior change. |

## Rules

- Do not duplicate function signatures or type hints in prose.
- Remove stale behavior instead of keeping history in reference docs (use `CHANGELOG.md`).
- Code examples must be executable Python, not pseudo-code.
- Public API docstrings: one-line summary in imperative mood, plus `Note:` only for non-obvious behavior or catchable package exceptions.
