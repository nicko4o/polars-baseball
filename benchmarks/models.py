from __future__ import annotations

import sys
from dataclasses import dataclass, field
from datetime import datetime


class BenchmarkError(Exception):
    """Base exception for benchmark framework."""


VALID_CACHE_STATES: frozenset[str] = frozenset({"cold", "warm", "null"})


def _raise_if_negative(name: str, value: float | int) -> None:
    if value < 0:
        raise BenchmarkError(f"{name} must be >= 0, got {value}")


@dataclass(frozen=True)
class BenchmarkDimensions:
    api: str
    start_date: str
    end_date: str
    team: str | None = None
    parallel: bool = True
    cache_state: str = "cold"
    concurrency: int | None = None

    def __post_init__(self) -> None:
        if self.cache_state not in VALID_CACHE_STATES:
            msg = f"Invalid cache_state={self.cache_state!r}; must be one of {sorted(VALID_CACHE_STATES)}"
            raise BenchmarkError(msg)
        if not self.start_date:
            raise BenchmarkError("start_date must not be empty")
        if not self.end_date:
            raise BenchmarkError("end_date must not be empty")


@dataclass(frozen=True)
class BenchmarkMetrics:
    wall_time_seconds: float
    cpu_time_seconds: float
    peak_python_mib: float
    gc_collections: int
    result_rows: int
    result_columns: int

    FLOAT_FIELDS: tuple[str, ...] = ("wall_time_seconds", "cpu_time_seconds", "peak_python_mib")
    INT_FIELDS: tuple[str, ...] = ("gc_collections", "result_rows", "result_columns")

    def __post_init__(self) -> None:
        for name in self.FLOAT_FIELDS:
            _raise_if_negative(name, getattr(self, name))
        for name in self.INT_FIELDS:
            _raise_if_negative(name, getattr(self, name))


@dataclass(frozen=True)
class BenchmarkRun:
    dimensions: BenchmarkDimensions
    metrics: BenchmarkMetrics
    timestamp: datetime
    version: str
    python_version: str = field(default_factory=lambda: sys.version.split()[0])
    platform: str = field(default_factory=lambda: sys.platform)
