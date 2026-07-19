from __future__ import annotations

from datetime import datetime

import pytest

from benchmarks.models import BenchmarkDimensions, BenchmarkError, BenchmarkMetrics, BenchmarkRun


class TestBenchmarkDimensions:
    def test_minimal_construction(self) -> None:
        dims = BenchmarkDimensions(api="statcast", start_date="2024-04-01", end_date="2024-04-07")
        assert dims.api == "statcast"
        assert dims.cache_state == "cold"
        assert dims.parallel is True
        assert dims.concurrency is None

    def test_all_fields(self) -> None:
        dims = BenchmarkDimensions(
            api="statcast",
            start_date="2024-04-01",
            end_date="2024-04-07",
            team="NYY",
            parallel=False,
            cache_state="warm",
            concurrency=3,
        )
        assert dims.team == "NYY"
        assert dims.parallel is False
        assert dims.cache_state == "warm"
        assert dims.concurrency == 3

    def test_invalid_cache_state_raises(self) -> None:
        with pytest.raises(BenchmarkError, match="Invalid cache_state"):
            BenchmarkDimensions(api="statcast", start_date="2024-04-01", end_date="2024-04-07", cache_state="hot")

    def test_empty_start_date_raises(self) -> None:
        with pytest.raises(BenchmarkError, match="start_date must not be empty"):
            BenchmarkDimensions(api="statcast", start_date="", end_date="2024-04-07")

    def test_empty_end_date_raises(self) -> None:
        with pytest.raises(BenchmarkError, match="end_date must not be empty"):
            BenchmarkDimensions(api="statcast", start_date="2024-04-01", end_date="")


class TestBenchmarkMetrics:
    def test_minimal_construction(self) -> None:
        metrics = BenchmarkMetrics(
            wall_time_seconds=1.0,
            cpu_time_seconds=0.5,
            peak_python_mib=50.0,
            gc_collections=10,
            result_rows=1000,
            result_columns=50,
        )
        assert metrics.wall_time_seconds == 1.0
        assert metrics.cpu_time_seconds == 0.5
        assert metrics.peak_python_mib == 50.0
        assert metrics.gc_collections == 10
        assert metrics.result_rows == 1000
        assert metrics.result_columns == 50

    def test_zero_values(self) -> None:
        metrics = BenchmarkMetrics(
            wall_time_seconds=0.0,
            cpu_time_seconds=0.0,
            peak_python_mib=0.0,
            gc_collections=0,
            result_rows=0,
            result_columns=0,
        )
        assert metrics.wall_time_seconds == 0.0

    def test_negative_wall_time_raises(self) -> None:
        with pytest.raises(BenchmarkError, match="wall_time_seconds must be >= 0"):
            BenchmarkMetrics(
                wall_time_seconds=-0.1,
                cpu_time_seconds=0.5,
                peak_python_mib=50.0,
                gc_collections=10,
                result_rows=1000,
                result_columns=50,
            )

    def test_negative_cpu_time_raises(self) -> None:
        with pytest.raises(BenchmarkError, match="cpu_time_seconds must be >= 0"):
            BenchmarkMetrics(
                wall_time_seconds=1.0,
                cpu_time_seconds=-0.1,
                peak_python_mib=50.0,
                gc_collections=10,
                result_rows=1000,
                result_columns=50,
            )

    def test_negative_peak_mib_raises(self) -> None:
        with pytest.raises(BenchmarkError, match="peak_python_mib must be >= 0"):
            BenchmarkMetrics(
                wall_time_seconds=1.0,
                cpu_time_seconds=0.5,
                peak_python_mib=-1.0,
                gc_collections=10,
                result_rows=1000,
                result_columns=50,
            )

    def test_negative_gc_collections_raises(self) -> None:
        with pytest.raises(BenchmarkError, match="gc_collections must be >= 0"):
            BenchmarkMetrics(
                wall_time_seconds=1.0,
                cpu_time_seconds=0.5,
                peak_python_mib=50.0,
                gc_collections=-1,
                result_rows=1000,
                result_columns=50,
            )

    def test_negative_result_rows_raises(self) -> None:
        with pytest.raises(BenchmarkError, match="result_rows must be >= 0"):
            BenchmarkMetrics(
                wall_time_seconds=1.0,
                cpu_time_seconds=0.5,
                peak_python_mib=50.0,
                gc_collections=10,
                result_rows=-1,
                result_columns=50,
            )


class TestBenchmarkRun:
    def test_construction(self) -> None:
        dims = BenchmarkDimensions(api="statcast", start_date="2024-04-01", end_date="2024-04-07")
        metrics = BenchmarkMetrics(
            wall_time_seconds=1.0,
            cpu_time_seconds=0.5,
            peak_python_mib=50.0,
            gc_collections=10,
            result_rows=1000,
            result_columns=50,
        )
        run = BenchmarkRun(
            dimensions=dims,
            metrics=metrics,
            timestamp=datetime(2024, 1, 1),
            version="0.1.0",
        )
        assert run.version == "0.1.0"
        assert isinstance(run.python_version, str)
        assert isinstance(run.platform, str)

    def test_default_python_version(self) -> None:
        import sys

        dims = BenchmarkDimensions(api="statcast", start_date="2024-04-01", end_date="2024-04-07")
        metrics = BenchmarkMetrics(
            wall_time_seconds=1.0,
            cpu_time_seconds=0.5,
            peak_python_mib=50.0,
            gc_collections=10,
            result_rows=1000,
            result_columns=50,
        )
        run = BenchmarkRun(
            dimensions=dims,
            metrics=metrics,
            timestamp=datetime(2024, 1, 1),
            version="0.1.0",
        )
        assert run.python_version == sys.version.split()[0]
