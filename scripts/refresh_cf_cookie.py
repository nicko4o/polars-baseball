"""Script to refresh Cloudflare Turnstile cookies and automatically update GitHub Secrets.

Usage:
    uv run python scripts/refresh_cf_cookie.py [--repo OWNER/REPO] [--dry-run]
"""

from __future__ import annotations

import argparse
import asyncio
import os
import shutil
import subprocess
import sys

DEFAULT_REPO = "nicko4o/polars-baseball"
TARGET_URLS = [
    "https://www.fangraphs.com/leaderboard/major-league",
    "https://www.baseball-reference.com",
]


async def _fetch_via_cffi() -> tuple[str | None, str | None]:
    try:
        from curl_cffi.requests import AsyncSession

        async with AsyncSession(impersonate="chrome") as session:
            for url in TARGET_URLS:
                resp = await session.get(url, timeout=15)
                if resp.status_code == 200:
                    cookies = session.cookies.get_dict()
                    cf_clearance = cookies.get("cf_clearance")
                    cookie_header = "; ".join(f"{k}={v}" for k, v in cookies.items() if "cf_" in k.lower())
                    if cookie_header or cf_clearance:
                        return cf_clearance, cookie_header
    except Exception as e:
        print(f"Notice: cffi fetch fallback note: {e}", file=sys.stderr)
    return None, None


async def _fetch_via_playwright() -> tuple[str | None, str | None]:
    try:
        from playwright.async_api import (  # type: ignore[import-not-found]  # pyright: ignore[reportMissingImports]
            async_playwright,
        )
    except ImportError:
        return None, None

    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context(
                user_agent=(
                    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                    "(KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"
                )
            )
            page = await context.new_page()
            print("Navigating via Playwright to solve Cloudflare challenge...")
            for url in TARGET_URLS:
                try:
                    await page.goto(url, wait_until="domcontentloaded", timeout=20000)
                    await page.wait_for_timeout(3000)
                    cookies = await context.cookies()
                    cf_clearance = next((c["value"] for c in cookies if c["name"] == "cf_clearance"), None)
                    cookie_header = "; ".join(
                        f"{c['name']}={c['value']}" for c in cookies if "cf_" in c["name"].lower()
                    )
                    if cookie_header or cf_clearance:
                        await browser.close()
                        return cf_clearance, cookie_header
                except Exception as page_exc:
                    print(f"Playwright navigation attempt failed for {url}: {page_exc}", file=sys.stderr)
            await browser.close()
    except Exception as exc:
        print(f"Notice: Playwright fetch note: {exc}", file=sys.stderr)
    return None, None


async def fetch_cf_cookies() -> tuple[str | None, str | None]:
    """Fetch Cloudflare clearance token using Playwright if available, or curl_cffi as fallback."""
    cf_clearance, cookie_header = await _fetch_via_playwright()
    if cookie_header or cf_clearance:
        return cf_clearance, cookie_header

    return await _fetch_via_cffi()


def update_gh_secret(secret_name: str, secret_value: str, repo: str) -> bool:
    """Update a GitHub repository secret using the gh CLI."""
    if not shutil.which("gh"):
        print("Error: GitHub CLI ('gh') is not installed or not in PATH.", file=sys.stderr)
        return False

    try:
        subprocess.run(
            ["gh", "secret", "set", secret_name, "--repo", repo],
            input=secret_value.encode("utf-8"),
            check=True,
            capture_output=True,
        )
        print(f"Successfully updated GitHub secret '{secret_name}' in repo '{repo}'.")
        return True
    except subprocess.CalledProcessError as e:
        stderr = e.stderr.decode("utf-8").strip() if e.stderr else str(e)
        print(f"Error: Failed to update secret '{secret_name}': {stderr}", file=sys.stderr)
        return False


async def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch Cloudflare cookies and update GitHub Secrets.")
    parser.add_argument(
        "--repo",
        default=os.environ.get("GITHUB_REPOSITORY", DEFAULT_REPO),
        help=f"Target GitHub repository (default: {DEFAULT_REPO})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Fetch cookies and print values without updating GitHub secrets",
    )
    args = parser.parse_args()

    print("Fetching Cloudflare clearance cookies...")
    cf_clearance, cookie_header = await fetch_cf_cookies()

    if not cookie_header and not cf_clearance:
        print(
            "Error: Could not retrieve Cloudflare cookies automatically.\n"
            "If Cloudflare Turnstile challenge blocks headless access, pass CF_COOKIE manually or install playwright.",
            file=sys.stderr,
        )
        return 1

    if args.dry_run:
        print("[Dry Run] Retrieved Cloudflare Cookies:")
        print(f"  CF_CLEARANCE: {cf_clearance}")
        print(f"  CF_COOKIE:    {cookie_header}")
        return 0

    success = True
    if cookie_header:
        if not update_gh_secret("CF_COOKIE", cookie_header, args.repo):
            success = False
    if cf_clearance:
        if not update_gh_secret("CF_CLEARANCE", cf_clearance, args.repo):
            success = False

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
