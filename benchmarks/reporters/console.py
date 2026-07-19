from __future__ import annotations

from rich.console import Console
from rich.table import Table

from benchmarks.models import BenchmarkRun

_console = Console()


def print_run(run: BenchmarkRun) -> None:
    dims = run.dimensions
    m = run.metrics
    table = Table(title=f"Benchmark: {dims.api} ({dims.cache_state}, parallel={dims.parallel})")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    table.add_row("wall_time", f"{m.wall_time_seconds:.3f} s")
    table.add_row("cpu_time", f"{m.cpu_time_seconds:.3f} s")
    table.add_row("peak_python_mem", f"{m.peak_python_mib:.2f} MiB")
    table.add_row("gc_collections", str(m.gc_collections))
    table.add_row("result_shape", f"{m.result_rows} x {m.result_columns}")
    table.add_row("version", run.version)
    _console.print(table)
