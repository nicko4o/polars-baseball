# Contributing to polars-baseball

Languages: [English](https://github.com/nicko4o/polars-baseball/blob/main/.github/CONTRIBUTING.md) | [Traditional Chinese](https://github.com/nicko4o/polars-baseball/blob/main/.github/CONTRIBUTING.zh-TW.md)

We welcome pull requests improving any aspect of this library! To maintain high code quality and runtime performance, we enforce strict architectural discipline.

The main ways to contribute to polars-baseball are:
* Scraping additional baseball data sources from trusted sites (FanGraphs, Baseball Reference, etc.).
* Fixing scraping/parsing bugs in the existing code.
* Improving documentation, typings, or tests.

---

## AI-Assisted Contributions Policy

We welcome AI-assisted contributions (using Copilot, ChatGPT, Claude, etc.), but we enforce a zero-tolerance policy for unchecked AI generation:
* **Full Accountability**: You are 100% responsible for every line of code you submit. You must fully understand and be able to explain the logic of your PR.
* **No Raw Dumps**: Do not submit copy-pasted code that you have not personally run, tested, and reviewed.
* **Hallucination Rejection**: PRs that include hallucinated library APIs or incorrect type assertions will be closed immediately without review.

---

## Design Principles

Our engineering philosophy favors:
- **Explicit over implicit**: Explicit parameters and contexts over magical assumptions.
- **Predictable APIs over clever abstractions**: Keep code readable and easy to follow.
- **Fail fast over silent recovery**: Raise diagnostic errors immediately rather than returning half-broken states.
- **Stable schemas over convenience**: Maintain deterministic DataFrame structures.
- **Composition over inheritance**: Keep helper components decoupled and interchangeable.

---

## Guidelines & Engineering Discipline

### 1. Polars & Async-First Architecture
* **Polars-First**: Public data APIs should return native `polars.DataFrame` objects (except documented exceptions like `standings()`). Never use Pandas.
* **Async-First**: Data-fetching APIs must be asynchronous (`async def`) and support custom `BaseballContext` injection for resource isolation.
* **Explicit Schemas**: Every returned DataFrame must be backed by an explicit Polars schema contract (e.g., `BWAR_BAT_SCHEMA`) defined within its parser or api module.
* **Public Exports**: New public entry points must be declared in `polars_baseball.__all__` and covered by contract tests.

### 2. Type Safety & Code Quality
* **Type Annotations**: Avoid `Any` or weak typing whenever a more precise type is practical. If `Any` is necessary (e.g., in fallback parsing or JSON structures), document the rationale.
* **MyPy Checks**: Code must pass strict type checking (`uv run mypy polars_baseball/`) with zero errors.
* **No Magic Constants**: Avoid embedding raw magic numbers or strings. Keep business logic constants centrally defined in enums or configurations.
* **Function Length**: Prefer small, cohesive functions. When a function grows beyond roughly 50 LOC, consider extracting smaller helper functions.
* **Fail Fast**: Write defensive code. Avoid swallowing exceptions or recovering silently from unexpected formats.

### 3. Caching & Docstring Semantics
* **Cache Semantics**: If an API reads, writes, partitions, or bypasses cached data, document its behavior (including cache location, cache key derivation, TTL, and force refresh mechanisms).
* **Docstring Guidelines**: Public API docstrings should document only behavior that cannot be inferred from function signatures or type hints. Do not duplicate type hints. Focus on:
  - Observable side effects (e.g., network calls, cache writes).
  - Behavioral contracts.
  - Compatibility or non-obvious edge cases.

---

## Project Layout

- `polars_baseball/apis/`: Stable, user-facing public API endpoints.
- `polars_baseball/gateways/`: Network boundaries, external HTTP client configurations, and data retrieval layers.
- `polars_baseball/parsers/`: Pure parsers utilizing the degradation/strategy pattern to transform raw data.
- `polars_baseball/schemas/`: Declarative schema structures and validation contracts.
- `polars_baseball/enums/`: Centralized domain-specific enums and constant tables.
- `polars_baseball/data/`: Static reference datasets (e.g., team ID mapping).

---

## Testing Philosophy

- **Prefer Unit Tests**: Validate parsing and business logic offline using mocked inputs from `tests/polars_baseball/data/`.
- **Avoid Network Requests**: Tests must not hit live servers by default.
- **Mark Live Tests**: Tests requiring internet connectivity must be marked with `@pytest.mark.live` and are skipped during regular CI pipeline runs.

---

## Development Workflow

### 1. Local Setup
We use `uv` for lightning-fast, reproducible dependency management.
```bash
# Fork and clone the repository
git clone git@github.com:<your GitHub handle>/polars-baseball.git
cd polars-baseball
git remote add upstream git@github.com:nicko4o/polars-baseball.git

# Initialize environment and install in editable mode with test dependencies
uv sync --all-extras
```

### 2. Running Verification Tools Locally
Before submitting a pull request, you **must** run the following verification checks:

* **Format and Linting**:
  ```bash
  uv run ruff check polars_baseball/ --fix
  uv run ruff format polars_baseball/
  ```
* **Run MyPy Type Check**:
  ```bash
  uv run mypy polars_baseball/
  # Or via Makefile:
  make mypy ONLY_MODIFIED=0
  ```
* **Run Tests**:
  ```bash
  uv run pytest tests/polars_baseball -m "not live"
  # Or via Makefile:
  make test TEST_FLAGS='-n auto -m "not live"'
  ```

### 3. Commit Message & Git Discipline
We strictly enforce **Conventional Commits**.
* Use prefixes like `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, or `ci:`.
* Example: `git commit -m "feat: add expected stats parser for statcast"`
* **Release Commits**: Commits representing official releases should be formatted as `release: vX.Y.Z` or `chore(release): vX.Y.Z`.
* Example: `release: v0.1.0 initial release of polars-baseball`

---

## Submitting a Pull Request

### 1. Branch Policy
* Create feature or bugfix branches from `main`.
* Open Pull Requests targeting `main`.
* All PRs targeting `main` must be merged via **Squash and Merge** to keep the release history clean.
* Direct commits or non-squashed merges to `main` are reserved exclusively for releases (with tags `vX.Y.Z`).

### 2. General Scope
* Keep your PR scope highly focused. Do not combine unrelated refactoring with feature development.
* Ensure new features are covered by unit tests under `tests/polars_baseball/`.
* Keep documentation under `docs/` updated if API signatures or behaviors change.

### 3. Out-of-Scope Contributions
The following changes are generally out of scope. Please open an issue or start a discussion before attempting:
- Formatting-only PRs (the repository uses auto-formatting on every build/CI run anyway).
- Large, unrelated refactoring in other modules while working on a feature.
- Introducing new third-party dependencies without prior maintainer approval.
- Breaking API schema changes without a pre-designed migration path.
