# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- Refactor `Makefile` according to GNU Make best practices: add `.PHONY` for all phony targets, add default `help` target, improve `git status` file detection for renamed files, and update `act` Docker runner image.

## [0.7.3] - 2026-07-20

### Fixed
- Make `FileCacheAdapter` fail-safe against read-only filesystems, permission issues, or disk-full conditions (`OSError`): on init directory creation failure the adapter disables itself with a logged warning; on write failure the adapter transitions to disabled mode so subsequent I/O operations are skipped entirely. `set()` no longer propagates `OSError` to callers (non-`OSError` exceptions still propagate).

## [0.7.2] - 2026-07-20

### Changed
- Replace `default_context()` (deprecated) + `_default_ctx` singleton with a thread-safe `BaseballContext.default()` classmethod and `reset_default()`; remove `_default_ctx`, `_default_ctx_lock`, `_default_context_resolver`, and `_set_default_cache_context_resolver()`. (Breaking change: internal only — `default_context()` not in `__all__`.)
- Ensure thread-safety of the context singleton and cleanup lifecycle operations using `threading.Lock`.
- Remove `default_context()` re-export from `polars_baseball/__init__.py`; re-export `cleanup` directly.
- Use `importlib.import_module` in `_cache.py` to avoid circular import of context module.
- Remove all `mock_default_ctx` / `@patch("polars_baseball.context.default_context")` patterns from tests; inject `BaseballContext` instances explicitly.

## [0.7.1] - 2026-07-20

### Added
- Add `team_ids` to root public API (`pb.team_ids`).
- Add docstrings to `CacheAdapter` ABC (get/set/clear/get_or_fetch/get_list/set_list), `FileCacheAdapter`, `NullCacheAdapter`, `GlobalCache`, and `cached`/`cached_list` decorators in `_cache.py`.
- Add docstrings to `CompiledTable`, `CompiledDatasetGateway` (all public methods), and module-level helpers in `gateways/compiled.py`.
- Add docstrings to `parsers/retrosheet.py` (6 parsing functions) and all `parsers/mlb/` modules (9 files, 15+ parse functions).
- Document docstring convention (`Note:` section) in `MAINTAINING.md`.

### Fixed
- Fix HTTP 403 Forbidden blocks when fetching FanGraphs data by excluding default `User-Agent` headers when `curl_cffi` browser impersonation is active.
- Fix all deprecation warnings in the test suite by explicitly using `BaseballContext` in contract tests, monkeypatching default context resolvers during test runs, and asserting warnings in fuzzy lookup tests.

### Changed
- Standardize docstring format: replace project-invented `Edge Cases:` sections with standard `Note:` across 24 files (~40 functions).
- Fix `add_spray_angle` removal version reference in `docs/reference/statcast.md` (was "version 2", never released).
- Remove redundant type signatures from `docs/reference/statcast.md` function listings.
- Improve `bwar_bat`/`bwar_pitch` and 5 Retrosheet gamelog function docstrings with note on delegation behavior.
- Add `benchmarks/` framework with structured benchmark runner, profiles, reporters (console via `rich`, JSON), and baseline tracking.
- Add `python -m benchmarks run` CLI replacing `examples/benchmark_statcast.py`.
- Add `python -m benchmarks baseline` CLI for managing historical benchmark data.
- Add `lahman_batting`, `lahman_pitching`, `lahman_people` profiles (compiled datasets, no network required).
- Add `standings_2024` profile with `list[polars.DataFrame]` return support.
- Runner now supports `list[polars.DataFrame]` return values via `_extract_shape` helper.

### Changed
- `examples/benchmark_statcast.py` removed in favour of `benchmarks/` CLI.
- `scripts/statcast_timing.py` marked deprecated; CI timing gate will migrate to `benchmarks/`.



## [0.7.0] - 2026-07-19

### Added
- Add `UpstreamUnavailableError` exception to distinguish empty upstream responses from empty result sets.
- Add `player_name_suggestions()` public API for fuzzy name matching, split from `playerid_lookup()`.
- Add `concurrency_limit` parameter to `statcast()`, `events()`, and `rosters()` to bound parallel requests.
- Make `HttpClient` constructor parameters configurable: `max_retries`, `retry_backoff_base_seconds`, `timeout`, `impersonate`, `default_headers`, `bref_requests_per_minute`.

### Changed
- Deprecate and remove Traditional Chinese reference documentation and guides under `docs/zh-tw/` to establish a single source of truth (SSOT) and reduce maintenance overhead.
- **Default cache changed to NullCacheAdapter**: `GlobalCache` no longer creates a file-backed cache directory on import. Call `configure_cache(Path)` or pass `FileCacheAdapter(...)` to `BaseballContext(cache=...)` explicitly.
- Gateway (`BRefGateway`, `SavantGateway`) empty upstream responses now raise `UpstreamUnavailableError` instead of silently returning empty DataFrames.
- Retrosheet `github_token` is now read explicitly from `BaseballContext.github_token` instead of environment variables.
- `playerid_lookup(fuzzy=True)` emits `DeprecationWarning`; fuzzy matching moved to `player_name_suggestions()`.
- `default_context()` emits `DeprecationWarning`; prefer `async with BaseballContext() as ctx:`.
- Concurrency bounded by `asyncio.Semaphore` in `statcast()`, `events()`, `rosters()`.

### Fixed
- Fix type hint contract and argument fallback logic in `CacheCallArgs.argument()`.
- Prevent concurrent initialization race conditions in player lookup by implementing a loop-local single-flight lock.
- Enable safe retry of player lookup initialization after transient loading failures.
- Preserve original accented player names during accent-insensitive lookup searches.
- Add support for string-based database IDs in `playerid_reverse_lookup` for Baseball Reference and Retrosheet.
- Retain the public schema contract for empty player lookup table results.
- Harden HTTP client routing by resolving policies via strict scheme/hostname origin matching.

## [0.6.0] - 2026-07-17

### Added
- Add local Markdown relative link regression test to prevent future documentation link degradation.

### Changed
- Consolidate reference documentation pages from 21 pages to 8 pages for both English and Traditional Chinese versions.
- Refactor core provider logic for better Separation of Concerns (SRP): introduce dedicated gateways for FanGraphs and Savant, extract a central HTTP routing policy, and isolate player search and lookup state into a specialized service.
- **BREAKING CHANGE**: Refactored internal caching decorators (`@cached`). Dynamic parameter binding using signature inspection has been replaced with the explicit, type-safe `CacheCallArgs` pattern.

## [0.5.0] - 2026-07-16

### Changed

- **BREAKING CHANGE**: Removed legacy FanGraphs root aliases (`fg_batting`, `fg_pitching`, `fg_fielding`, `fg_team_batting`, `fg_team_pitching`, `fg_team_fielding`). Use `polars_baseball.fangraphs.*` instead.
- Simplify documentation structure: reorganize documents into `guides/` and `reference/` directories, introduce `api_index.md` for task-based API selection, and establish `MAINTAINING.md` rules.

## [0.4.0] - 2026-07-16

### Changed

- **BREAKING CHANGE**: Remove provider-prefixed root aliases for MLB Stats API and Baseball Savant APIs. Use `polars_baseball.mlb.*` and `polars_baseball.savant.*` instead.

### Fixed

- Fix assertion type check in `test_live_mlb_standings` to match the single DataFrame return contract.
- Refactor `scripts/verify_all_apis.py` to use the new namespaces (`mlb.*` and `savant.*`) rather than legacy internal functions.

## [0.3.0] - 2026-07-15

### Added

- Add FanGraphs direct helper functions (`fg_batting`, `fg_pitching`, `fg_fielding`, `fg_team_batting`, `fg_team_pitching`, `fg_team_fielding`) and the `polars_baseball.fangraphs` namespace while preserving `FanGraphsRequest` and `fg_data`.
- Add `polars_baseball.savant` and `polars_baseball.mlb` provider namespaces while preserving existing root-level functions.
- Add `start_date` and `end_date` aliases for `statcast`, `statcast_batter`, and `statcast_pitcher`.

### Changed

- Update English and Traditional Chinese documentation to prefer the new provider namespaces, FanGraphs helpers, and Statcast date aliases.

## [0.2.0] - 2026-07-15

### Added
- Expose BRef (`bwar_bat`, `bwar_pitch`), Lahman database tables, Retrosheet datasets, and PlayerID utility functions directly from the package root (`polars_baseball`).
- Add a public `close()` lifecycle method to `BaseballContext` for clean connection teardown.
- Add SEO keywords to `pyproject.toml`.
- Configure Codecov integration for automated test coverage tracking.

### Changed
- **BREAKING CHANGE**: Change `standings()` return type from `list[polars.DataFrame]` to a single `polars.DataFrame` containing season, division_id, and division_name columns.
- **BREAKING CHANGE**: Change `retrosheet.events()` return type from `dict[str, bytes]` to a single `polars.DataFrame` with season, event_type, filename, and content (Binary) columns.
- Update documentation and caching guide examples to reflect the direct root namespace imports and `context.close()` lifecycle.
- Add documentation badges to `README.md` and `README.zh-TW.md`.

### Fixed
- Correct non-working email address (`nicko4o@users.noreply.github.com`) in `CODE_OF_CONDUCT.md` and `CODE_OF_CONDUCT.zh-TW.md` to reference the GitHub profile contact info.


## [0.1.1] - 2026-07-15

### Added
- Introduce Jupyter Notebook usage guide (`docs/jupyter.md` and `docs/zh-tw/jupyter.md`).
- Add executable scripts in `examples/` for onboarding and benchmarking (`statcast_pitch_mix.py`, `fangraphs_leaderboard.py`, `mlb_schedule.py`, `benchmark_statcast.py`).
- Add nightly smoke tests to proactively detect future Baseball Savant schema changes before they impact production.

### Fixed
- Correct non-executable code blocks in documentation examples.
- Fix relative language switcher links in `.github/` files to prevent 404 resolution (using absolute URLs for `SECURITY.md` and `CONTRIBUTING.md`).
- Fix relative image links in `statcast_utils.md` documentation pages.
- Resolve a crash (`SchemaError`) when fetching Statcast data across multiple dates. The library now dynamically aligns column types when data chunks have inconsistent structures.
- Ensure new Statcast tracking metrics (e.g., `bat_speed`, `swing_length`, `miss_distance`) are consistently parsed as numeric values (`Float64`) instead of raw strings.

## [0.1.0] - 2026-07-14

### Added

- **Initial Release**: Retrieve baseball data in Python using Polars.
- Supports Statcast, Baseball Reference, FanGraphs, Lahman, Retrosheet, and MLB Stats API.
- Native asynchronous engine with built-in caching adapter.
- Fully typed public APIs and Traditional Chinese documentation.
- Integrated repository templates and Contributor Covenant Code of Conduct.
