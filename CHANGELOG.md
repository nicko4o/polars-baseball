# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.7.5] - 2026-07-22

### Fixed
- Prevent silent swallowing of critical system exceptions (e.g. `MemoryError`) during cache reads and schema validation.
- Harden error boundary handling during data parsing to ensure unexpected exceptions fail fast instead of resulting in corrupt state.

## [0.7.4] - 2026-07-21

### Fixed
- Fix potential deadlock in `SharedExclusiveLock` caused by signal interruptions during asynchronous lock waiting.
- Fix table rendering and data extraction in `BRefCSVExportStrategy` when processing tables with nested `<th>` tags or escaped commas.
- Optimize hot cache retrieval performance by bypassing lock contention on pre-cached responses.
- Update internal dependencies (`pillow`, `pytest`) to remediate known security vulnerabilities.
- Fix version synchronization between `pyproject.toml` and `polars_baseball.__version__`.

### Changed
- Update PyPI maturity classifier to `Beta` (`Development Status :: 4 - Beta`).

## [0.7.3] - 2026-07-20

### Fixed
- Gracefully handle read-only filesystems or permission errors in `FileCacheAdapter` by failing safe to a disabled cache state without raising unhandled `OSError` exceptions.

## [0.7.2] - 2026-07-20

### Added
- Expose `team_ids` helper in root public API (`polars_baseball.team_ids`).
- Add comprehensive `benchmarks` suite and CLI runner for historical baseline tracking.

### Changed
- Standardize full asynchronous context management via `BaseballContext.default()` and `reset_default()`.
- Refactor and standardize docstring formats across all gateway and parser modules.

### Fixed
- Fix HTTP 403 Forbidden errors when fetching FanGraphs endpoints under active browser impersonation.

## [0.7.0] - 2026-07-19

### Added
- Add `UpstreamUnavailableError` exception to distinguish empty upstream data responses from valid empty result sets.
- Add `player_name_suggestions()` public API for fuzzy name matching.
- Add `concurrency_limit` parameter to `statcast()`, `events()`, and `rosters()`.
- Add configurable options for HTTP client timeouts, retries, and rate limits.

### Changed
- **Default cache changed to NullCacheAdapter**: `GlobalCache` no longer implicitly creates cache files on import. Explicit configuration via `configure_cache()` or `BaseballContext(cache=...)` is required.
- Deprecate fuzzy matching in `playerid_lookup()`; use `player_name_suggestions()` instead.
- Deprecate legacy `default_context()`; prefer `async with BaseballContext() as ctx:`.

### Fixed
- Fix race conditions during initial player lookup initialization.
- Retain accented characters in original player names during lookup operations.
- Support string-based player IDs in reverse lookup functions.

## [0.6.0] - 2026-07-17

### Changed
- Refactor core providers into dedicated gateways (`BRefGateway`, `SavantGateway`) with central HTTP routing policy.
- **BREAKING CHANGE**: Refactor internal caching decorator (`@cached`) to use explicit `CacheCallArgs` typing.

## [0.5.0] - 2026-07-16

### Changed
- **BREAKING CHANGE**: Remove legacy FanGraphs root aliases (`fg_batting`, `fg_pitching`, etc.). Use `polars_baseball.fangraphs.*` instead.

## [0.4.0] - 2026-07-16

### Changed
- **BREAKING CHANGE**: Remove provider-prefixed root aliases for MLB Stats API and Savant APIs. Use `polars_baseball.mlb.*` and `polars_baseball.savant.*` instead.

## [0.3.0] - 2026-07-15

### Added
- Add sub-namespace modules `polars_baseball.fangraphs`, `polars_baseball.savant`, and `polars_baseball.mlb`.
- Add `start_date` and `end_date` aliases for Statcast functions.

## [0.2.0] - 2026-07-15

### Added
- Expose BRef (`bwar_bat`, `bwar_pitch`), Lahman database tables, and Retrosheet datasets directly from root package.

### Changed
- **BREAKING CHANGE**: Change `standings()` return type from `list[polars.DataFrame]` to a single unified `polars.DataFrame`.
- **BREAKING CHANGE**: Change `retrosheet.events()` return type to a single unified `polars.DataFrame`.

## [0.1.1] - 2026-07-15

### Fixed
- Fix `SchemaError` crash when fetching Statcast data across dates with inconsistent columns.
- Ensure Statcast tracking metrics (`bat_speed`, `swing_length`) parse cleanly as `Float64`.

## [0.1.0] - 2026-07-14

### Added
- Initial Release: Asynchronous baseball data library for Python built on Polars.
