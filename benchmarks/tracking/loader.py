from __future__ import annotations

import json
from pathlib import Path
from typing import cast

from benchmarks.models import BaselineRecord

BASELINE_FILE = Path("benchmarks/tracking/baseline.json")


def load_baseline(path: Path = BASELINE_FILE) -> list[BaselineRecord]:
    if not path.exists():
        return []
    return cast("list[BaselineRecord]", json.loads(path.read_text()))


def save_baseline(records: list[BaselineRecord], path: Path = BASELINE_FILE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(records, indent=2))
