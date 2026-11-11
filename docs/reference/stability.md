# Stability & Upstream Schema Policy

This document defines the interface stability guarantees, Semantic Versioning (SemVer) policies, and upstream data drift handling rules for `polars-baseball`.

---

## Semantic Versioning Guarantees

`polars-baseball` adheres to [Semantic Versioning 2.0.0](https://semver.org/).

Given a version number `MAJOR.MINOR.PATCH`:
- **MAJOR** version bumps indicate breaking changes to the stable SDK interface.
- **MINOR** version bumps indicate backwards-compatible feature additions or deprecation announcements.
- **PATCH** version bumps indicate backwards-compatible bug fixes and upstream parser adaptations.

---

## SDK Surface Stability

The following SDK components constitute the stable public interface:

1. **Client Lifecycle & Namespaces**:
   - `BaseballClient` instantiation, configuration parameters (`http`, `cache`, `cache_dir`, `github_token`), and context manager lifecycle (`__aenter__`, `__aexit__`, `close()`, `aclose()`).
   - Provider namespace accessors: `client.savant`, `client.mlb`, `client.fangraphs`, `client.bref`, `client.retrosheet`, `client.lahman`, and `client.lookup`.
2. **Method Signatures & Parameter Semantics**:
   - Public method names, positional/keyword arguments, default values, and parameter types across all client namespaces.
   - All data retrieval methods are asynchronous (`async def`) and return `polars.DataFrame` (or `polars.LazyFrame` for partitioned parquet scanning).
3. **Exception Hierarchy**:
   - Exceptions derived from `PolarsBaseballError` (`InvalidParameterError`, `UpstreamUnavailableError`, `UpstreamParseError`, `PolarsBaseballHttpError`, `UpstreamDataCorruptedError`).
4. **Enums & Public Utilities**:
   - Root exports: `BaseballClient`, `KeyType`, `Position`.

---

## Upstream Data Drift Policy

`polars-baseball` retrieves data from third-party and unofficial baseball data providers (MLB Stats API, Baseball Savant, FanGraphs, Baseball Reference, and Retrosheet). Upstream providers occasionally modify unannounced response formats or deprecate metrics without notice.

To balance SDK reliability with real-world sports data dynamics:

### 1. Tier-1: Core Identity Columns (Guaranteed)
Core entity identifiers, dates, and primary keys are guaranteed across minor releases:
- Player identity keys: `player_id`, `mlbam_id`, `key_mlbam`, `key_fangraphs`, `key_bbref`.
- Game identity keys: `game_pk`, `game_date`, `season`.
- Base tabular structure: output always resolves to a valid tabular `polars.DataFrame` or empty DataFrame with typed schema.

### 2. Tier-2: Upstream Raw Metrics (Drift Tolerant)
Advanced metrics, tracking attributes, and provider-specific calculation fields (e.g., newly added Statcast bat tracking metrics, modified Statcast column names such as `spin_rate_deprecated`, or FanGraphs custom leaderboard columns):
- Upstream additions or removals of secondary metric columns **do not constitute a breaking change** for the library.
- When an upstream provider alters, drops, or renames raw columns, `polars-baseball` adapts parser schemas and normalization pipelines in **patch** or **minor** releases.
- Schema conflicts across heterogeneous date queries are automatically coalesced and normalized without data loss.

---

## Provider Service Levels & Best-Effort Scrapers

`polars-baseball` categorizes data providers into two distinct operational tiers:

### Tier 1: Structured APIs & Compiled Archives (High Reliability)
- **MLB Stats API (`client.mlb.*`)**, **Baseball Savant (`client.savant.*`)**, **Retrosheet (`client.retrosheet.*`)**, and **Lahman (`client.lahman.*`)**.
- These providers offer structured JSON, CSV, or archival data endpoints without active anti-bot gates. They are considered highly reliable for automated data pipelines.

### Tier 2: Unofficial Web Scrapers (Best-Effort & Anti-Bot Protected)
- **FanGraphs (`client.fangraphs.*`)** and **Baseball Reference (`client.bref.*`)**.
- These providers rely on HTML table parsing and undocumented internal query endpoints. Both sites employ Cloudflare Turnstile anti-bot protection and strict rate limiting.
- **Service Level Guarantee**: Access to Tier 2 sources is provided strictly on a **best-effort basis**. Users must respect provider Terms of Service, configure conservative rate limits (`bref_requests_per_minute`), pass clearance tokens via `extra_headers` (`CF_CLEARANCE`, `CF_COOKIE`) when prompted, or rely on local parquet cache. Uninterrupted availability cannot be guaranteed if upstream anti-bot policies change.

---

## Deprecation Lifecycle

When a public API method or parameter is scheduled for deprecation:

1. **Announcement**: The symbol raises a `DeprecationWarning` (`stacklevel=2`) explaining the replacement method and scheduled removal version.
2. **Horizon**: Deprecated symbols will survive for at least **one minor release** before removal.
3. **Changelog**: All deprecations and removals are documented under the `Deprecated` and `Removed` sections of `CHANGELOG.md` following the [Keep a Changelog](https://keepachangelog.com/) standard.
