from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from benchmarks.models import BenchmarkDimensions, BenchmarkMetrics, BenchmarkRun


def _dimensions_to_dict(d: BenchmarkDimensions) -> dict[str, Any]:
    return {
        "api": d.api,
        "start_date": d.start_date,
        "end_date": d.end_date,
        "team": d.team,
        "parallel": d.parallel,
        "cache_state": d.cache_state,
        "concurrency": d.concurrency,
    }


def _metrics_to_dict(m: BenchmarkMetrics) -> dict[str, Any]:
    return {
        "wall_time_seconds": m.wall_time_seconds,
        "cpu_time_seconds": m.cpu_time_seconds,
        "peak_python_mib": m.peak_python_mib,
        "gc_collections": m.gc_collections,
        "result_rows": m.result_rows,
        "result_columns": m.result_columns,
    }


def run_to_dict(run: BenchmarkRun) -> dict[str, Any]:
    return {
        "dimensions": _dimensions_to_dict(run.dimensions),
        "metrics": _metrics_to_dict(run.metrics),
        "timestamp": run.timestamp.isoformat(),
        "version": run.version,
        "python_version": run.python_version,
        "platform": run.platform,
    }


def dump_json(run: BenchmarkRun, path: str | Path | None = None) -> str:
    data = run_to_dict(run)
    text = json.dumps(data, indent=2)
    if path is not None:
        Path(path).write_text(text)
    return text
