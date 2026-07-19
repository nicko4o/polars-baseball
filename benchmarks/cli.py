from __future__ import annotations

import argparse
import asyncio
import sys

from benchmarks.profiles import PROFILES
from benchmarks.reporters.console import print_run
from benchmarks.reporters.json_reporter import dump_json, run_to_dict
from benchmarks.runner import run_benchmark
from benchmarks.tracking.comparator import check_regression
from benchmarks.tracking.loader import load_baseline, save_baseline


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m benchmarks",
        description="Benchmark runner for polars-baseball",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    run_parser = sub.add_parser("run", help="Run a benchmark profile")
    run_parser.add_argument(
        "profile", choices=list(PROFILES) + ["list"], help='Profile name (or "list" to show available)'
    )
    run_parser.add_argument("--json", action="store_true", help="Output JSON instead of rich table")
    run_parser.add_argument("--json-file", type=str, default=None, help="Write JSON to file")
    run_parser.add_argument("--baseline", action="store_true", help="Compare against saved baseline")
    run_parser.add_argument("--fail-if-regression", action="store_true", help="Exit non-zero if regression detected")

    baseline_parser = sub.add_parser("baseline", help="Manage baselines")
    baseline_parser.add_argument(
        "action", choices=["show", "clear"], help="show: display saved baselines, clear: delete all"
    )

    return parser


def _list_profiles() -> None:
    print("Available profiles:")
    for name in sorted(PROFILES):
        p = PROFILES[name]
        d = p.dimensions
        print(f"  {name}: {d.api} [{d.start_date} .. {d.end_date}] parallel={d.parallel} cache={d.cache_state}")


async def _run_profile(args: argparse.Namespace) -> int:
    if args.profile == "list":
        _list_profiles()
        return 0

    profile = PROFILES.get(args.profile)
    if profile is None:
        print(f"Unknown profile: {args.profile}", file=sys.stderr)
        return 1

    dims = profile.dimensions
    kwargs = profile.to_kwargs()

    run = await run_benchmark(profile.fn, dims, **kwargs)

    if args.json or args.json_file:
        text = dump_json(run, path=args.json_file)
        if args.json:
            print(text)
    else:
        print_run(run)

    if args.baseline or args.fail_if_regression:
        history = load_baseline()
        result = check_regression(run.metrics.wall_time_seconds, history)
        if result.is_regression:
            print(
                f"REGRESSION: wall_time {result.current_value:.3f}s vs "
                f"baseline {result.baseline_mean:.3f}s "
                f"(+{result.sigma:.1f} sigma)"
            )
            if args.fail_if_regression:
                return 1
        else:
            print(
                f"OK: wall_time {result.current_value:.3f}s "
                f"(baseline {result.baseline_mean:.3f}s, sigma={result.sigma:.1f})"
            )
        history.append(run_to_dict(run))
        save_baseline(history)

    return 0


def _handle_baseline(args: argparse.Namespace) -> int:
    if args.action == "show":
        history = load_baseline()
        if not history:
            print("No baseline data")
            return 0
        for i, rec in enumerate(history):
            d = rec.get("dimensions", {})
            m = rec.get("metrics", {})
            print(
                f"[{i}] {d.get('api', '?')}: "
                f"wall={m.get('wall_time_seconds', '?')}s "
                f"mem={m.get('peak_python_mib', '?')}MiB "
                f"({rec.get('timestamp', '')})"
            )
    elif args.action == "clear":
        save_baseline([])
        print("Baseline cleared")
    return 0


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()
    if args.command == "run":
        return asyncio.run(_run_profile(args))
    elif args.command == "baseline":
        return _handle_baseline(args)
    return 1


if __name__ == "__main__":
    sys.exit(main())
