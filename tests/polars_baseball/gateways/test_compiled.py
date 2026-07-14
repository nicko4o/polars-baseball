import io
import zipfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from polars_baseball._cache import FileCacheAdapter
from polars_baseball.context import BaseballContext
from polars_baseball.exceptions import UpstreamParseError
from polars_baseball.gateways.compiled import CompiledDatasetGateway, CompiledTable

ARCHIVE_URL = "https://example.test/archive.zip"


def _archive(csv_text: str, filename: str = "source/data/table.csv") -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr(filename, csv_text)
    return buffer.getvalue()


@pytest.mark.asyncio
async def test_compiled_gateway_writes_table_parquet_once(tmp_path: Path) -> None:
    mock_http = MagicMock()
    mock_http.get_bytes = AsyncMock(return_value=_archive("id,name\n1,Ada\n"))
    ctx = BaseballContext(http=mock_http, cache=FileCacheAdapter(tmp_path))
    table = CompiledTable(
        dataset="demo",
        table_name="data/table",
        archive_url=ARCHIVE_URL,
        archive_member="source/data/table.csv",
    )

    gateway = CompiledDatasetGateway(ctx)
    first = await gateway.read_table(table)
    second = await gateway.read_table(table)

    assert first.equals(second)
    assert first["name"][0] == "Ada"
    assert (tmp_path / "compiled-datasets" / "demo" / "data" / "table.parquet").exists()
    assert mock_http.get_bytes.await_count == 1


@pytest.mark.asyncio
async def test_compiled_gateway_supports_uncached_reads(tmp_path: Path) -> None:
    mock_http = MagicMock()
    mock_http.get_bytes = AsyncMock(return_value=_archive("id,name\n1,Ada\n"))
    ctx = BaseballContext(http=mock_http, cache=FileCacheAdapter(tmp_path))
    table = CompiledTable(
        dataset="demo",
        table_name="data/table",
        archive_url=ARCHIVE_URL,
        archive_member="source/data/table.csv",
    )

    gateway = CompiledDatasetGateway(ctx)
    await gateway.read_table(table, use_cache=False)
    await gateway.read_table(table, use_cache=False)

    assert not (tmp_path / "compiled-datasets").exists()
    assert mock_http.get_bytes.await_count == 2


@pytest.mark.asyncio
async def test_compiled_gateway_fails_when_archive_member_missing(tmp_path: Path) -> None:
    mock_http = MagicMock()
    mock_http.get_bytes = AsyncMock(return_value=_archive("id,name\n1,Ada\n", filename="README.md"))
    ctx = BaseballContext(http=mock_http, cache=FileCacheAdapter(tmp_path))
    table = CompiledTable(
        dataset="demo",
        table_name="data/table",
        archive_url=ARCHIVE_URL,
        archive_member="source/data/table.csv",
    )

    gateway = CompiledDatasetGateway(ctx)

    with pytest.raises(UpstreamParseError, match="source/data/table.csv"):
        await gateway.read_table(table)


@pytest.mark.asyncio
async def test_compiled_gateway_can_match_archive_member_pattern(tmp_path: Path) -> None:
    mock_http = MagicMock()
    mock_http.get_bytes = AsyncMock(return_value=_archive("id,name\n1,Ada\n", filename="source/data/people.csv"))
    ctx = BaseballContext(http=mock_http, cache=FileCacheAdapter(tmp_path))
    table = CompiledTable(
        dataset="demo",
        table_name="people",
        archive_url=ARCHIVE_URL,
        archive_member_pattern=r"/people\.csv$",
    )

    gateway = CompiledDatasetGateway(ctx)
    df = await gateway.read_table(table)

    assert df["name"][0] == "Ada"


def test_write_bytes_atomic_cleanup_on_error(tmp_path: Path) -> None:
    from unittest.mock import patch

    from polars_baseball.gateways.compiled import _write_bytes_atomic

    target_file = tmp_path / "target.txt"

    with patch.object(Path, "write_bytes", side_effect=OSError("Disk full")):
        with pytest.raises(OSError, match="Disk full"):
            _write_bytes_atomic(target_file, b"some raw bytes")

    assert not target_file.exists()
    tmp_files = list(tmp_path.glob("*.tmp"))
    assert len(tmp_files) == 0
