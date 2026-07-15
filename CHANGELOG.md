# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Fixed
- Correct non-executable code blocks in documentation examples.
- Fix relative language switcher links in `.github/` files to prevent 404 resolution (using absolute URLs for `SECURITY.md` and `CONTRIBUTING.md`).
- Fix relative image links in `statcast_utils.md` documentation pages.

### Added
- Introduce Jupyter Notebook usage guide (`docs/jupyter.md` and `docs/zh-tw/jupyter.md`).

## [0.1.0] - 2026-07-14

### Added

- **Initial Release**: Retrieve baseball data in Python using Polars.
- Supports Statcast, Baseball Reference, FanGraphs, Lahman, Retrosheet, and MLB Stats API.
- Native asynchronous engine with built-in caching adapter.
- Fully typed public APIs and Traditional Chinese documentation.
- Integrated repository templates and Contributor Covenant Code of Conduct.
