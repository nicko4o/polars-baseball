from __future__ import annotations

import argparse
import hashlib
import io
import json
from pathlib import Path
from typing import Final, Literal

import httpx
import polars as pl

from polars_baseball._config import CHADWICK_REGISTER_ARCHIVE_URL, LAHMAN_ARCHIVE_URL
from polars_baseball.apis.lahman import LAHMAN_DATASET, LAHMAN_TABLE_FILES, _lahman_table
from polars_baseball.apis.playerid import (
    CHADWICK_REGISTER_DATASET,
    _chadwick_people_table,
    _normalize_chadwick_register,
)
from polars_baseball.gateways.compiled import PARQUET_SUFFIX, CompiledTable, read_archive_table_bytes

DEFAULT_OUTPUT_DIR: Final[Path] = Path("dist/compiled-datasets")
MANIFEST_FILENAME: Final[str] = "manifest.json"
HTTP_TIMEOUT_SECONDS: Final[float] = 60.0
DatasetName = Literal["all", "lahman", "chadwick-register"]


def _download_archive(url: str) -> bytes:
    with httpx.Client(timeout=HTTP_TIMEOUT_SECONDS, follow_redirects=True) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.content


def _sha256(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def _write_table(output_dir: Path, table: CompiledTable, df: pl.DataFrame) -> dict[str, object]:
    path = output_dir / table.dataset / f"{table.table_name}{PARQUET_SUFFIX}"
    path.parent.mkdir(parents=True, exist_ok=True)
    buffer = io.BytesIO()
    df.write_parquet(buffer)
    raw = buffer.getvalue()
    path.write_bytes(raw)
    return {
        "dataset": table.dataset,
        "table": table.table_name,
        "path": str(path.relative_to(output_dir)),
        "rows": df.height,
        "columns": {name: str(dtype) for name, dtype in df.schema.items()},
        "sha256": _sha256(raw),
    }


def _compile_lahman(output_dir: Path) -> list[dict[str, object]]:
    raw_archive = _download_archive(LAHMAN_ARCHIVE_URL)
    entries: list[dict[str, object]] = []
    for filepath in LAHMAN_TABLE_FILES:
        table = _lahman_table(filepath, quote_char='"')
        df = read_archive_table_bytes(raw_archive, table)
        entries.append(_write_table(output_dir, table, df))
    return entries


def _compile_chadwick(output_dir: Path) -> list[dict[str, object]]:
    raw_archive = _download_archive(CHADWICK_REGISTER_ARCHIVE_URL)
    table = _chadwick_people_table()
    raw_df = read_archive_table_bytes(raw_archive, table)
    df = _normalize_chadwick_register(raw_df)
    return [_write_table(output_dir, table, df)]


def _write_manifest(output_dir: Path, entries: list[dict[str, object]]) -> None:
    manifest = {
        "format": "polars-baseball-compiled-datasets-v1",
        "sources": {
            LAHMAN_DATASET: LAHMAN_ARCHIVE_URL,
            CHADWICK_REGISTER_DATASET: CHADWICK_REGISTER_ARCHIVE_URL,
        },
        "tables": entries,
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / MANIFEST_FILENAME).write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")


def compile_datasets(dataset: DatasetName, output_dir: Path) -> None:
    entries: list[dict[str, object]] = []
    if dataset in ("all", "lahman"):
        entries.extend(_compile_lahman(output_dir))
    if dataset in ("all", "chadwick-register"):
        entries.extend(_compile_chadwick(output_dir))
    _write_manifest(output_dir, entries)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Compile upstream baseball CSV archives into parquet datasets.")
    parser.add_argument(
        "--dataset",
        choices=("all", "lahman", "chadwick-register"),
        default="all",
        help="Dataset to compile.",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory where parquet files and manifest are written.",
    )
    return parser.parse_args()


def main() -> None:
    args = _parse_args()
    compile_datasets(args.dataset, args.output_dir)


if __name__ == "__main__":
    main()
