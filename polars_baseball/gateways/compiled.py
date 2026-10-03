import asyncio
import io
import re
import zipfile
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import polars as pl

from polars_baseball._config import COMPILED_DATASETS_ROOT_URL
from polars_baseball._storage_primitives import (
    atomic_write_bytes,
    atomic_write_parquet,
    get_file_lock,
    resolve_cache_dir,
    validate_safe_path_component,
    validate_zip_archive,
)
from polars_baseball.context import BaseballContext
from polars_baseball.exceptions import (
    UpstreamDataCorruptedError,
    UpstreamParseError,
    UpstreamStructureChangedError,
)

COMPILED_DATASETS_DIR: Final[str] = "compiled-datasets"
ARCHIVES_DIR: Final[str] = "_archives"
PARQUET_SUFFIX: Final[str] = ".parquet"
ZIP_SUFFIX: Final[str] = ".zip"
DEFAULT_CSV_INFER_SCHEMA_LENGTH: Final[int] = 10000


@dataclass(frozen=True)
class CompiledTable:
    """Descriptor for a single table within a compiled dataset archive.

    Attributes:
        dataset: Logical dataset name (namespace for grouping tables).
        table_name: Table identifier used in cache file naming.
        archive_url: Remote URL for the ZIP archive containing this table.
        archive_member: Exact member path within the ZIP archive.
        archive_member_pattern: Regex pattern to locate the member when
            the exact path is unknown.
        quote_char: CSV quote character.
        infer_schema_length: Row count to sample for CSV schema inference.
    """

    dataset: str
    table_name: str
    archive_url: str
    archive_member: str | None = None
    archive_member_pattern: str | None = None
    quote_char: str = '"'
    infer_schema_length: int = DEFAULT_CSV_INFER_SCHEMA_LENGTH

    def __post_init__(self) -> None:
        validate_safe_path_component(self.dataset)
        validate_safe_path_component(self.table_name)
        if self.archive_member is None and self.archive_member_pattern is None:
            raise ValueError("CompiledTable requires archive_member or archive_member_pattern.")


class CompiledDatasetGateway:
    """Gateway for lazy-compiled datasets (Lahman, Chadwick, etc.).

    Supports two backends:
        1. Remote Parquet CDN (when COMPILED_DATASETS_ROOT_URL is set).
        2. On-demand compilation from upstream ZIP archives.
    """

    def __init__(self, context: BaseballContext) -> None:
        self._context = context
        self._cache_dir = resolve_cache_dir(context)

    async def ensure_archive(self, dataset: str, archive_url: str) -> Path:
        """Download and validate the ZIP archive for a dataset, or return cached path.

        Note:
            Validates ZIP integrity after download. Raises UpstreamDataCorruptedError
            for invalid archives.
        """
        validate_safe_path_component(dataset)
        archive_path = self._archive_path(dataset)
        async with get_file_lock(str(archive_path)):
            if not archive_path.exists():
                raw = await self._context.http.get_bytes(archive_url)
                await asyncio.to_thread(atomic_write_bytes, archive_path, raw)
            await asyncio.to_thread(validate_zip_archive, archive_path)
        return archive_path

    async def table_path(self, table: CompiledTable) -> Path:
        """Resolve the local Parquet path for a table, compiling from archive if needed.

        Note:
            Requires a file-backed cache directory. Raises UpstreamParseError
            when cache_dir is None.
        """
        if self._cache_dir is None:
            raise UpstreamParseError("Compiled dataset table paths require a file-backed cache directory.")
        path = self._table_path(table)
        async with get_file_lock(str(path)):
            if not path.exists():
                df = await self._fetch_table(table)
                await asyncio.to_thread(atomic_write_parquet, path, df)
        return path

    async def scan_table(self, table: CompiledTable) -> pl.LazyFrame:
        """Return a lazy Parquet scan handle for this table.

        Note:
            Compiles the table first if no cached Parquet exists.
        """
        path = await self.table_path(table)
        return pl.scan_parquet(path)

    async def read_table(self, table: CompiledTable, *, use_cache: bool = True) -> pl.DataFrame:
        """Read the full table into memory.

        Note:
            When use_cache is False or no cache_dir is configured,
            fetches directly from upstream without local persistence.
        """
        if not use_cache or self._cache_dir is None:
            return await self._fetch_table_uncached(table)
        lazy_frame = await self.scan_table(table)
        return lazy_frame.collect()

    def _table_path(self, table: CompiledTable) -> Path:
        return self._file_cache_dir() / COMPILED_DATASETS_DIR / table.dataset / f"{table.table_name}{PARQUET_SUFFIX}"

    def _archive_path(self, dataset: str) -> Path:
        return self._file_cache_dir() / COMPILED_DATASETS_DIR / ARCHIVES_DIR / f"{dataset}{ZIP_SUFFIX}"

    def _file_cache_dir(self) -> Path:
        if self._cache_dir is None:
            raise UpstreamParseError("Compiled datasets require a file-backed cache directory for file paths.")
        return self._cache_dir

    async def _fetch_table(self, table: CompiledTable) -> pl.DataFrame:
        if COMPILED_DATASETS_ROOT_URL:
            return await self._fetch_remote_parquet(table)
        return await self._fetch_archive_csv(table)

    async def _fetch_table_uncached(self, table: CompiledTable) -> pl.DataFrame:
        if COMPILED_DATASETS_ROOT_URL:
            return await self._fetch_remote_parquet(table)
        raw = await self._context.http.get_bytes(table.archive_url)
        return await asyncio.to_thread(read_archive_table_bytes, raw, table)

    async def _fetch_remote_parquet(self, table: CompiledTable) -> pl.DataFrame:
        url = f"{COMPILED_DATASETS_ROOT_URL}/{table.dataset}/{table.table_name}{PARQUET_SUFFIX}"
        raw = await self._context.http.get_bytes(url)
        return pl.read_parquet(io.BytesIO(raw))

    async def _fetch_archive_csv(self, table: CompiledTable) -> pl.DataFrame:
        archive_path = await self.ensure_archive(table.dataset, table.archive_url)
        return await asyncio.to_thread(_read_archive_csv, archive_path, table)


def _read_archive_zip_to_df(file_or_bytes: Path | bytes, table: CompiledTable, error_message: str) -> pl.DataFrame:
    try:
        file_like = io.BytesIO(file_or_bytes) if isinstance(file_or_bytes, bytes) else file_or_bytes
        with zipfile.ZipFile(file_like) as archive:
            member = _resolve_archive_member(archive, table)
            raw = archive.read(member)
        return _read_csv_bytes(raw, table)
    except zipfile.BadZipFile as err:
        raise UpstreamDataCorruptedError(error_message) from err


def _read_archive_csv(path: Path, table: CompiledTable) -> pl.DataFrame:
    return _read_archive_zip_to_df(path, table, f"Bad zip file: {path}")


def read_archive_table_bytes(raw_archive: bytes, table: CompiledTable) -> pl.DataFrame:
    """Read a table directly from in-memory archive bytes without caching.

    Note:
        Uses archive_member or archive_member_pattern to locate the CSV
        within the ZIP. Raises UpstreamStructureChangedError when the
        expected member is not found.
    """
    return _read_archive_zip_to_df(raw_archive, table, "Bad zip file data")


def _read_csv_bytes(raw: bytes, table: CompiledTable) -> pl.DataFrame:
    return pl.read_csv(
        raw,
        quote_char=table.quote_char,
        infer_schema_length=table.infer_schema_length,
        null_values=[""],
    )


def _resolve_archive_member(archive: zipfile.ZipFile, table: CompiledTable) -> str:
    if table.archive_member is not None:
        if table.archive_member in archive.namelist():
            return table.archive_member
        raise UpstreamStructureChangedError(f"Compiled table archive member not found: {table.archive_member}")

    if table.archive_member_pattern is None:
        raise UpstreamStructureChangedError(f"Compiled table has no archive member selector: {table.table_name}")

    pattern = re.compile(table.archive_member_pattern)
    for name in archive.namelist():
        if pattern.search(name):
            return name
    raise UpstreamStructureChangedError(
        f"Compiled table archive member pattern not found: {table.archive_member_pattern}"
    )
