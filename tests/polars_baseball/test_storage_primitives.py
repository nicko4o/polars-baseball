from pathlib import Path

import polars as pl
import pytest

from polars_baseball._storage_primitives import (
    atomic_write_bytes,
    atomic_write_file,
    atomic_write_parquet,
    get_file_lock,
    resolve_cache_dir,
    validate_safe_path_component,
    validate_zip_archive,
)
from polars_baseball.context import BaseballContext
from polars_baseball.exceptions import UpstreamDataCorruptedError


def test_validate_safe_path_component() -> None:
    validate_safe_path_component("valid_name")
    validate_safe_path_component("folder/file.csv")

    with pytest.raises(ValueError, match="Unsafe compiled dataset path"):
        validate_safe_path_component("")

    with pytest.raises(ValueError, match="Unsafe compiled dataset path"):
        validate_safe_path_component("/absolute/path")

    with pytest.raises(ValueError, match="Unsafe compiled dataset path"):
        validate_safe_path_component("../parent")


def test_atomic_write_and_read(tmp_path: Path) -> None:
    target_bytes = tmp_path / "subdir" / "data.bin"
    atomic_write_bytes(target_bytes, b"test binary data")
    assert target_bytes.read_bytes() == b"test binary data"

    target_pq = tmp_path / "subdir" / "data.parquet"
    df = pl.DataFrame({"x": [1, 2, 3]})
    atomic_write_parquet(target_pq, df)
    read_df = pl.read_parquet(target_pq)
    assert read_df.equals(df)


def test_atomic_write_cleans_up_on_failure(tmp_path: Path) -> None:
    target = tmp_path / "fail.bin"

    def faulty_writer(path: Path) -> None:
        path.write_bytes(b"temp")
        raise RuntimeError("write aborted")

    with pytest.raises(RuntimeError, match="write aborted"):
        atomic_write_file(target, faulty_writer)

    assert not target.exists()
    assert list(tmp_path.glob("*.tmp")) == []


def test_validate_zip_archive(tmp_path: Path) -> None:
    bad_zip = tmp_path / "corrupted.zip"
    bad_zip.write_bytes(b"not a real zip")

    with pytest.raises(UpstreamDataCorruptedError):
        validate_zip_archive(bad_zip)


@pytest.mark.asyncio
async def test_get_file_lock_deduplication() -> None:
    lock1 = get_file_lock("resource_key")
    lock2 = get_file_lock("resource_key")
    assert lock1 is lock2


def test_resolve_cache_dir(tmp_path: Path) -> None:
    ctx = BaseballContext.with_file_cache(tmp_path)
    assert resolve_cache_dir(ctx) == tmp_path
