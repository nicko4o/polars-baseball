# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed
- Add documentation badges to `README.md` and `README.zh-TW.md`.
- Add SEO keywords to `pyproject.toml`.
- Configure Codecov integration for automated test coverage tracking.

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
