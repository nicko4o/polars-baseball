from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

BASELINE_FILE = Path("benchmarks/tracking/baseline.json")


def load_baseline(path: Path = BASELINE_FILE) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return cast("list[dict[str, Any]]", json.loads(path.read_text()))


def save_baseline(records: list[dict[str, Any]], path: Path = BASELINE_FILE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(records, indent=2))
