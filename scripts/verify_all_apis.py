"""Comprehensive live verification script for all polars-baseball data sources.

Usage:
    uv run python scratch/verify_all_apis.py

Environment variables:
    CF_CLEARANCE     — cf_clearance cookie value for BRef/FG Cloudflare bypass
    CF_COOKIE        — full Cookie header (overrides CF_CLEARANCE)
    USER_AGENT       — custom User-Agent for BRef/FG requests
    SKIP_BREF        — set to "1" to skip BRef tests
    SKIP_FG          — set to "1" to skip FanGraphs tests
    SKIP_SAVANT      — set to "1" to skip Savant tests
    SKIP_MLB_API     — set to "1" to skip MLB Stats API tests
    SKIP_COMPILED    — set to "1" to skip compiled dataset tests
    SKIP_RETROSHEET  — set to "1" to skip Retrosheet tests
"""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path

import polars as pl

from polars_baseball import (
    bwar_bat,
    cleanup,
    configure_cache,
    fg_data,
    mlb,
    prospect_rankings,
    savant,
    standings,
)
from polars_baseball.apis.fangraphs import FanGraphsRequest
from polars_baseball.apis.lahman import people as lahman_people
from polars_baseball.apis.playerid import chadwick_register, playerid_lookup
from polars_baseball.apis.retrosheet import schedules as retrosheet_schedules
from polars_baseball.context import BaseballContext, default_context

GAME_PK = 823359
PLAYER_ID = 660271
TEAM_ID = 108

RowCount = int
ColCount = int


@dataclass
class ApiTestResult:
    name: str
    source: str
    success: bool
    row_count: RowCount = 0
    col_count: ColCount = 0
    error: str | None = None
    duration_sec: float = 0.0


@dataclass
class TestCase:
    name: str
    source: str
    fn: Callable[[], Awaitable[pl.DataFrame | list[pl.DataFrame]]]


_CF_SOURCES: frozenset[str] = frozenset({"BRef", "FanGraphs"})


def _is_cf_block(error: str) -> bool:
    return "403" in error and ("Cloudflare" in error or "BRef" in error or "FanGraphs" in error)


def _has_cf_bypass() -> bool:
    return bool(os.environ.get("CF_CLEARANCE") or os.environ.get("CF_COOKIE"))


def _configure_http_client(ctx: BaseballContext) -> None:
    cf_clearance = os.environ.get("CF_CLEARANCE")
    cf_cookie = os.environ.get("CF_COOKIE")
    user_agent = os.environ.get("USER_AGENT")
    if not (cf_clearance or cf_cookie or user_agent):
        return

    extra_headers = {}
    if cf_cookie:
        extra_headers["Cookie"] = cf_cookie
    elif cf_clearance:
        extra_headers["Cookie"] = f"cf_clearance={cf_clearance}"
    if user_agent:
        extra_headers["User-Agent"] = user_agent

    ctx.http.extra_headers = extra_headers


async def _run_test(test: TestCase) -> ApiTestResult:
    start = time.time()
    try:
        result = await test.fn()
        elapsed = time.time() - start

        if isinstance(result, list):
            if not result:
                return ApiTestResult(test.name, test.source, True, 0, 0, duration_sec=elapsed)
            rows = sum(d.height for d in result)
            cols = result[0].width
            return ApiTestResult(test.name, test.source, True, rows, cols, duration_sec=elapsed)

        return ApiTestResult(
            test.name,
            test.source,
            True,
            result.height,
            result.width,
            duration_sec=elapsed,
        )
    except Exception as exc:
        elapsed = time.time() - start
        return ApiTestResult(test.name, test.source, False, error=str(exc), duration_sec=elapsed)


def _build_tests() -> list[TestCase]:
    tests: list[TestCase] = []

    if os.environ.get("SKIP_SAVANT") != "1":
        tests += [
            TestCase(
                "statcast_range_3day", "Savant", lambda: savant.statcast("2023-08-01", "2023-08-03", verbose=False)
            ),
            TestCase("statcast_single_game", "Savant", lambda: savant.single_game(GAME_PK)),
            TestCase("savant_exitvelo_barrels", "Savant", lambda: savant.exitvelo_barrels(2023)),
            TestCase("savant_outs_above_average", "Savant", lambda: savant.outs_above_average(2023, pos="CF")),
            TestCase("savant_gamefeed_exit_velocity", "Savant", lambda: savant.gamefeed_exit_velocity(GAME_PK)),
            TestCase("savant_gamefeed_pitch_data", "Savant", lambda: savant.gamefeed_pitch_data(GAME_PK)),
        ]

    if os.environ.get("SKIP_BREF") != "1":
        tests += [
            TestCase("bref_bwar_bat", "BRef", lambda: bwar_bat(return_all=False)),
        ]

    if os.environ.get("SKIP_FG") != "1":
        tests += [
            TestCase(
                "fangraphs_batting",
                "FanGraphs",
                lambda: fg_data(
                    FanGraphsRequest.from_raw(
                        start_season=2023,
                        stats_category="bat",
                        league="all",
                        qual=0,
                    )
                ),
            ),
        ]

    if os.environ.get("SKIP_MLB_API") != "1":
        tests += [
            TestCase("mlb_teams", "MLB_API", lambda: mlb.teams(season=2023)),
            TestCase("mlb_divisions", "MLB_API", lambda: mlb.divisions()),
            TestCase("mlb_leagues", "MLB_API", lambda: mlb.leagues()),
            TestCase("mlb_people", "MLB_API", lambda: mlb.people([PLAYER_ID])),
            TestCase("mlb_people_awards", "MLB_API", lambda: mlb.people_awards(PLAYER_ID)),
            TestCase("mlb_schedule", "MLB_API", lambda: mlb.schedule(2023, team_id=108)),
            TestCase("mlb_roster", "MLB_API", lambda: mlb.roster(TEAM_ID, 2023)),
            TestCase("mlb_player_stats", "MLB_API", lambda: mlb.player_stats(PLAYER_ID, "hitting", season=2023)),
            TestCase("mlb_game_boxscore", "MLB_API", lambda: mlb.game_boxscore(GAME_PK)),
            TestCase("mlb_game_boxscore_stats", "MLB_API", lambda: mlb.game_boxscore_stats(GAME_PK)),
            TestCase("mlb_game_play_by_play", "MLB_API", lambda: mlb.game_play_by_play(GAME_PK)),
            TestCase("mlb_game_win_probability", "MLB_API", lambda: mlb.game_win_probability(GAME_PK)),
            TestCase("mlb_stat_leaders", "MLB_API", lambda: mlb.stat_leaders(season=2023, categories=["homeRuns"])),
            TestCase("mlb_team_stats", "MLB_API", lambda: mlb.team_stats(TEAM_ID, season=2023, group="hitting")),
            TestCase("mlb_postseason_schedule", "MLB_API", lambda: mlb.postseason_schedule(season=2023)),
            TestCase("mlb_draft", "MLB_API", lambda: mlb.draft(2023)),
            TestCase("mlb_pitch_arsenal", "MLB_API", lambda: mlb.pitch_arsenal(PLAYER_ID, 2023)),
            TestCase("mlb_transactions", "MLB_API", lambda: mlb.transactions(date="2023-06-01")),
            TestCase("mlb_venues", "MLB_API", lambda: mlb.venues(10)),
            TestCase("mlb_game_feed_live", "MLB_API", lambda: mlb.game_feed_live(GAME_PK)),
            TestCase("mlb_game_linescore", "MLB_API", lambda: mlb.game_linescore(GAME_PK)),
            TestCase("mlb_standings", "MLB_API", lambda: standings(2023)),
            TestCase("mlb_prospect_rankings", "MLB_API", lambda: prospect_rankings("top100", 2023)),
        ]

    if os.environ.get("SKIP_COMPILED") != "1":
        tests += [
            TestCase("lahman_people", "Compiled", lambda: lahman_people()),
            TestCase("chadwick_register", "Compiled", lambda: chadwick_register()),
            TestCase("playerid_lookup", "Compiled", lambda: playerid_lookup("Trout", "Mike")),
        ]

    if os.environ.get("SKIP_RETROSHEET") != "1":
        tests += [
            TestCase("retrosheet_schedules", "Retrosheet", lambda: retrosheet_schedules(2023)),
        ]

    return tests


async def main() -> int:
    tmp_dir = Path(tempfile.mkdtemp(prefix="pbb_verify_"))
    configure_cache(tmp_dir)

    ctx = default_context()
    _configure_http_client(ctx)

    tests = _build_tests()

    if not tests:
        print("No tests to run (all sources skipped via env vars).")
        return 0

    total = len(tests)

    print("=" * 66)
    print(f"  polars-baseball Live API Verification  ({total} tests)")
    print("=" * 66)
    print()

    results: list[ApiTestResult] = []
    for i, test in enumerate(tests, 1):
        label = f"[{i}/{total}]"
        print(f"{label} {test.name:40s}  ", end="", flush=True)
        result = await _run_test(test)
        results.append(result)

        status = "PASS" if result.success else "FAIL"
        detail = ""
        if result.success:
            detail = f"  ({result.row_count} rows, {result.col_count} cols)"
        else:
            detail = f"  {result.error}"
        print(f"{status:4s}{detail}")

    fail_count = sum(1 for r in results if not r.success)
    pass_count = total - fail_count

    cf_fails = sum(
        1 for r in results if not r.success and r.source in _CF_SOURCES and r.error and _is_cf_block(r.error)
    )
    real_fails = fail_count - cf_fails

    print("=" * 66)
    print("  Summary by Source")
    print("=" * 66)

    sources = sorted({r.source for r in results})
    for src in sources:
        src_results = [r for r in results if r.source == src]
        src_pass = sum(1 for r in src_results if r.success)
        src_total = len(src_results)
        src_cf = sum(1 for r in src_results if not r.success and r.error and _is_cf_block(r.error))
        suffix = ""
        if src_cf:
            suffix = f"  ({src_cf} blocked by Cloudflare)"
        print(f"  {src:15s}  {src_pass:2d}/{src_total:2d} passed{suffix}")

    print()
    if cf_fails:
        print(f"  {cf_fails} failure(s) caused by Cloudflare Turnstile (expected).")
        if not _has_cf_bypass():
            print("  Set CF_CLEARANCE or CF_COOKIE env vars to test BRef/FanGraphs fully.")
    print(f"  Total: {pass_count}/{total} passed, {real_fails} real failure(s)")
    print("=" * 66)

    for f in tmp_dir.iterdir():
        try:
            if f.is_file():
                f.unlink()
        except OSError:
            pass
    try:
        tmp_dir.rmdir()
    except OSError:
        pass

    await cleanup()

    return 1 if real_fails > 0 else 0


if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    sys.exit(asyncio.run(main()))
