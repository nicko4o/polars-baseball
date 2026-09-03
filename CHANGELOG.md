# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.21.2] - 2026-09-03

### Added

- `pb.standings()` now accepts a keyword-only `force_update: bool = False` parameter. Pass `True` to bypass the file cache and re-fetch fresh standings from the MLB Stats API — useful when calling across multiple seasons in long-running processes.

### Fixed

- Fix FanGraphs leaderboards (`pb.fg_data()`, `pb.fangraphs.*`) raising `UpstreamStructureChangedError` when queries match zero players; now safely returns an empty DataFrame.
- Fix `pb.mlb.schedule()` and `pb.mlb.game_boxscore()` returning schema-less DataFrames when no records are found; now consistently preserves typed empty schemas.
- Fix Statcast multi-query schema alignment for unrecognized columns with mixed string and numeric values to safely fall back to `pl.String`, preventing silent data loss.
- `pb.mlb.game_boxscore_stats()` now includes seven previously missing per-pitcher columns: `pitching_wins`, `pitching_losses`, `pitching_saves`, `pitching_holds`, `pitching_blownSaves`, `pitching_inheritedRunners`, and `pitching_inheritedRunnersScored`. These columns were returned by the MLB Stats API but were not propagated to the output DataFrame.

## [0.21.1] - 2026-08-24

### Fixed
- Fix `pb.mlb.game_highlights()` (and `mlb_game_highlights()`) producing `null` in `playId` column by reading `guid` from upstream highlight items (#125).
- Fix `pb.mlb.game_feed_live()` (and `mlb_game_feed_live()`) producing `null` in `playId` column by reading `playId` from individual pitch events.

## [0.21.0] - 2026-08-23

### Added
- Add `play_id`, `inning`, `half_inning`, `batter_id`, `pitcher_id`, `description`, and `des` columns to `pb.savant.gamefeed_exit_velocity()` (and `savant_gamefeed_exit_velocity()`) output DataFrame for play-level identification and context matching.
- Add `description` column to `pb.mlb.game_highlights()` (and `mlb_game_highlights()`) output DataFrame for detailed highlight context and scenario descriptions.

## [0.20.2] - 2026-08-18

### Added
- `reset_lookup_table()` to discard the in-memory player lookup table, forcing the next player lookup to reload it from upstream.

### Fixed
- Raise `UpstreamDataCorruptedError` instead of uncaught `zipfile.BadZipFile` when validating corrupted ZIP archives in compiled datasets (such as Lahman database and Chadwick register).

## [0.20.1] - 2026-08-18

### Fixed
- Fix BRef HTML table parsing when table contains multi-tier `<thead>` headers or subheader rows.

## [0.20.0] - 2026-08-17

### Added
- `sync_statcast()` (and `pb.savant.sync_statcast()`) to scrape and persist full-season Statcast pitch data as Hive-partitioned Parquet files in the local compiled dataset (`{cache_dir}/compiled-datasets/statcast/year={year}/statcast.parquet`), with atomic writes and optional `force_update`.
- `scan_statcast()` (and `pb.savant.scan_statcast()`) to lazily scan the local Statcast compiled dataset as a `polars.LazyFrame`, with predicate and projection pushdown, `auto_download` for missing seasons, and cross-year schema normalization.

## [0.19.1] - 2026-08-14

### Added
- Add `best_mp4_url` column to `pb.mlb.game_highlights()` output DataFrame as an alias of `url` for cross-API naming consistency with `film_room_search`.

### Fixed
- Fix `pb.mlb.film_room_search()` returning empty DataFrame when `limit > 20` by aligning pagination chunk size with upstream constraints and handling empty page early termination.
- Fix `pb.mlb.film_room_search()` producing missing MP4 video URLs by generating fallback MLB Cuts CDN URLs from media playback IDs.
- Allow `pb.mlb.film_room_search()` `date_range` parameter to accept Python `datetime.date`, `datetime.datetime` objects, and ISO 8601 timestamp strings in addition to `YYYY-MM-DD` strings.

## [0.19.0] - 2026-08-14

### Added
- `mlb_film_room_search()` (and `pb.mlb.film_room_search()`) to search MLB Film Room video clips across players, teams, seasons, date ranges, pitch types, hit results, exit velocity, and hit distance, returning a flattened `polars.DataFrame` with high-bitrate MP4 URLs and HLS streams.

## [0.18.0] - 2026-08-11

### Added
- `mlb_game_highlights()` (and `pb.mlb.game_highlights()`) to fetch single-game video highlight metadata and MP4 playback URLs from the MLB Stats API as a `polars.DataFrame`.

## [0.17.0] - 2026-08-11

### Added
- `pb.savant.park_factors()` to fetch Statcast Park Factors from Baseball Savant with support for single years, multi-year lists, year range tuples `(start_year, end_year)`, and venue filtering.
- Register `SavantEmbeddedJSONStrategy` into the global Savant leaderboard parsing chain, enabling extraction of embedded `var data = [...]` payloads across all Savant leaderboard endpoints.
- `HttpClient` and `BaseballContext` automatically detect and pass `CF_COOKIE`, `CF_CLEARANCE`, and `USER_AGENT` environment variables in HTTP request headers for Cloudflare-protected providers (FanGraphs, BRef).

## [0.16.1] - 2026-08-04

### Fixed
- Importing `polars_baseball` no longer creates the default cache directory. The directory is initialized only when a cached request is made.
- Concurrent cache reads, writes, and clearing are synchronized to prevent cache entries from reappearing after a clear operation.
- Savant leaderboard responses with malformed HTML now raise an upstream structure error instead of silently returning an empty table.

## [0.16.0] - 2026-08-03

### Removed
- **Breaking**: Remove the deprecated batter-specific Savant leaderboard functions (`pb.savant.batter_exitvelo_barrels`, `pb.savant.batter_expected_stats`, `pb.savant.batter_pitch_arsenal`, `pb.savant.batter_bat_tracking`, `pb.savant.batter_run_value`). Use the unified `player_type` APIs (`pb.savant.exitvelo_barrels`, etc.) instead.
- **Breaking**: Remove the deprecated camelCase minimum-threshold parameters on Savant leaderboard functions (`minBBE`, `minPA`, `minSwings`, `minP`, `min_count`). Use the snake_case forms instead.

## [0.15.0] - 2026-08-03

### Deprecated
- The legacy batter-specific Savant leaderboard functions (`pb.savant.batter_exitvelo_barrels`, `pb.savant.batter_expected_stats`, `pb.savant.batter_pitch_arsenal`, `pb.savant.batter_bat_tracking`, `pb.savant.batter_run_value`) and the camelCase minimum-threshold parameters (`minBBE`, `minPA`, `minSwings`, `minP`, `min_count`) are scheduled for removal in `v0.16.0`. Deprecation warnings now state the removal version. Migrate to the unified `player_type` APIs and snake_case parameters before then.

## [0.14.0] - 2026-08-03

### Added
- Accept `datetime.date` objects (in addition to `YYYY-MM-DD` strings) for date parameters on `pb.statcast`, `pb.statcast_batter`, `pb.statcast_pitcher`, `pb.mlb.schedule`, `pb.mlb.player_stats`, and `pb.mlb.transactions`.
- Export `Position`, `FangraphsStatsCategory`, `FangraphsMonth`, `FangraphsLeague`, `FangraphsPositions`, and `FangraphsStatColumn` from the package root (`pb.*`) for typed parameter discovery.
- Emit a `UserWarning` pointing to `pb.player_name_suggestions` when `pb.playerid_lookup` finds no matching player.
- Export `MlbStatsGroup` and `MlbRosterType` enums from the package root (`pb.*`) for typed parameter discovery.

### Changed
- `pb.savant.*` leaderboard functions accept snake_case thresholds (`min_bbe`, `min_pa`, `min_swings`, `min_pitches`) instead of camelCase; `pb.mlb.player_stats`, `pb.mlb.team_stats`, and `pb.mlb.stat_leaders` accept `MlbStatsGroup`; `pb.mlb.roster` accepts `MlbRosterType`.
- `pb.mlb.schedule` rejects a combination of `season` and `date`; `pb.mlb.transactions` rejects combining `date` with `start_date`/`end_date`. Pass only one filter at a time.
- `pb.player_name_suggestions` now ignores unrelated names instead of returning arbitrary rows for garbage input.

### Deprecated
- Legacy batter-specific Savant leaderboard functions (`pb.savant.batter_exitvelo_barrels`, `pb.savant.batter_expected_stats`, `pb.savant.batter_pitch_arsenal`, `pb.savant.batter_bat_tracking`, `pb.savant.batter_run_value`). Use the unified `player_type` APIs (`pb.savant.exitvelo_barrels`, etc.) instead.
- CamelCase minimum-threshold parameters on Savant leaderboard functions (`minBBE`, `minPA`, `minSwings`, `minP`, `min_count`). Use the snake_case forms instead.

### Fixed
- Fix broken code examples in the error-handling guide, Retrosheet reference, and player-lookup reference that referenced removed or renamed parameters.

## [0.13.1] - 2026-07-29

### Fixed
- Fix client-side filtering behavior for `pb.fangraphs.*` endpoints so passed `filters` (e.g., `filters=[("HR", ">", 30)]`) correctly filter rows on the returned DataFrame.
- Fix Polars schema inference errors across MLB Stats API endpoints by passing `infer_schema_length=None` for sparse optional response fields.




## [0.13.0] - 2026-07-28

### Added
- Add `FanGraphsFilter` / `FanGraphsFilterOp` typed filter API and tuple shorthand (`filters=[("HR", ">", 40)]`) for stat-level leaderboard filtering on FanGraphs.
- Add `filters`, `on_active_roster`, `minimum_age`, `maximum_age`, `players` parameters to all `pb.fangraphs.*` convenience functions.
- `FanGraphsRequest` factory methods now use explicit parameter signatures instead of `Unpack[TypedDict]` — IDE autocomplete now works.

## [0.12.0] - 2026-07-28

### Removed
- **Breaking**: Remove flat provider dataset exports (`batting`, `pitching`, `fielding`, `events`, `bwar_bat`, `bwar_pitch`, etc.) from root package namespace (`polars_baseball.__all__`). Use explicit provider namespaces instead (`pb.lahman.*`, `pb.retrosheet.*`, `pb.bref.*`).
- **Breaking**: Remove deprecated `start_dt` and `end_dt` parameter aliases from `statcast()`, `statcast_batter()`, and `statcast_pitcher()`. Use `start_date` and `end_date` instead.
- **Breaking**: Remove deprecated `return_all` parameter from `bwar_bat()` and `bwar_pitch()`. Use `all_columns` instead.
- **Breaking**: Remove deprecated `type` parameter alias from `retrosheet.events()`. Use `game_type` instead.
- **Breaking**: Remove deprecated `fuzzy` parameter from `playerid_lookup()` and `PlayerLookupService.search()`. Use `player_name_suggestions()` for fuzzy name matching.

## [0.11.0] - 2026-07-28

### Added
- Add `polars_baseball.lahman`, `polars_baseball.retrosheet`, and `polars_baseball.bref` provider namespace modules to unify provider-based API routing across all data sources (`pb.savant`, `pb.mlb`, `pb.fangraphs`, `pb.lahman`, `pb.retrosheet`, `pb.bref`).

## [0.10.0] - 2026-07-27

### Added
- Add `position` and `stat_columns` parameters to `pb.fangraphs.team_batting()`, `team_pitching()`, `team_fielding()`, `team_starters()`, and `team_relievers()`.

## [0.9.0] - 2026-07-27

### Added
- Add `pb.fangraphs.team_starters()` and `pb.fangraphs.team_relievers()` convenience wrappers for team-level starter and reliever pitching splits.
- Add Output DataFrame Schema tables across provider reference docs with links to internal schema modules.
- Add Error Handling & Production Resilience guide (`docs/guides/error_handling.md`).

## [0.8.1] - 2026-07-24

### Fixed
- Remove unused `pyarrow` dependency from `pyproject.toml`.

## [0.8.0] - 2026-07-23

### Added
- Add `context` parameter to `playerid_lookup`, `player_name_suggestions`, `player_search_list`, and `playerid_reverse_lookup` for lifecycle control.
- Add `all_columns` parameter to `bwar_bat` and `bwar_pitch` (replaces deprecated `return_all`).

### Changed
- **Breaking**: Rename `events(type=)` parameter to `events(game_type=)`. The `type` keyword still works with a deprecation warning.
- **Breaking**: Remove internal infrastructure classes from `polars_baseball.__all__` (`HttpClient`, `CacheAdapter`, `FileCacheAdapter`, `NullCacheAdapter`). `FanGraphsRequest` and `fg_data` remain exposed at top-level.
- **Breaking**: `bwar_bat` and `bwar_pitch` `return_all` parameter renamed to `all_columns`. The old name emits a deprecation warning.
- Unify Statcast date parameters: `start_date`/`end_date` are the canonical names. `start_dt`/`end_dt` now emit deprecation warnings.
- Update documentation examples to import `FanGraphsRequest`/`fg_data` from `polars_baseball.apis.fangraphs`.

## [0.7.6] - 2026-07-23

### Added
- Add `notebooks/` directory with interactive Jupyter demos for Statcast, FanGraphs, and MLB Stats API workflows.

### Changed
- Update all documentation examples and CLI defaults from 2024 to 2026 season.
- Add player ID lookup guidance in Statcast and MLB API reference docs.

### Fixed
- Fix Statcast API `ReadTimeout` for large queries by increasing default timeout from 30s to 60s.
- Fix broken API calls and column names in `mlb_schedule_demo.ipynb` — schedule/roster/standings schemas use camelCase, not snake_case.
- Fix `BaseballContext.__aexit__` swallowing critical system exceptions (`KeyboardInterrupt`, `SystemExit`) during context manager cleanup.
- Fix `playerid_reverse_lookup` to accept string-formatted player IDs for `MLBAM` and `FanGraphs` key types.
- Fix non-UTF-8 character parsing in Retrosheet datasets by adding fallback to Latin-1 decoding.
- Fix string parsing for missing and NaN values in Savant gamefeed data.

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
