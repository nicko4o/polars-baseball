from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest
from curl_cffi.requests.exceptions import ConnectionError as CurlConnectionError

from polars_baseball._cache import FileCacheAdapter
from polars_baseball._client import HttpClient
from polars_baseball.context import BaseballContext
from polars_baseball.exceptions import (
    ClientError,
    InvalidParameterError,
    InvalidSchemaError,
    PolarsBaseballError,
    PolarsBaseballHttpError,
    PolarsBaseballTransportError,
    ServerError,
    UpstreamDataCorruptedError,
    UpstreamParseError,
    UpstreamStructureChangedError,
)


def test_cache_get_raises_on_corrupt_file(tmp_path: Path) -> None:
    adapter = FileCacheAdapter(cache_dir=tmp_path)
    key = "corrupt_key"
    cache_file = tmp_path / "corrupt_key.parquet"
    cache_file.write_text("this is not a valid parquet file")

    assert adapter.get(key) is None
    assert not cache_file.exists()


def test_cache_clear_removes_cache_files(tmp_path: Path) -> None:
    adapter = FileCacheAdapter(cache_dir=tmp_path / "cache")
    adapter.set("k", pl.DataFrame({"x": [1]}))

    adapter.clear()

    assert not adapter.cache_dir.exists()


@pytest.mark.asyncio
async def test_client_bref_get_wraps_curl_request_error() -> None:
    client = HttpClient()
    mock_session = MagicMock()
    mock_session.get = AsyncMock(side_effect=CurlConnectionError("DNS failure"))

    with patch.object(client, "get_cffi_session", return_value=mock_session):
        with pytest.raises(PolarsBaseballTransportError, match="BRef network request failed"):
            await client.get_text("https://www.baseball-reference.com/dummy")


# ── Exception Hierarchy ───────────────────────────────────────────────────────


def test_client_error_is_polars_baseball_error() -> None:
    assert issubclass(ClientError, PolarsBaseballError)


def test_server_error_is_polars_baseball_error() -> None:
    assert issubclass(ServerError, PolarsBaseballError)


def test_invalid_parameter_error_is_client_error() -> None:
    assert issubclass(InvalidParameterError, ClientError)


def test_upstream_parse_error_is_server_error() -> None:
    assert issubclass(UpstreamParseError, ServerError)


def test_upstream_structure_changed_error_is_upstream_parse_error() -> None:
    assert issubclass(UpstreamStructureChangedError, UpstreamParseError)


def test_upstream_data_corrupted_error_is_upstream_parse_error() -> None:
    assert issubclass(UpstreamDataCorruptedError, UpstreamParseError)


def test_upstream_structure_changed_error_is_server_error() -> None:
    assert issubclass(UpstreamStructureChangedError, ServerError)


def test_upstream_data_corrupted_error_is_server_error() -> None:
    assert issubclass(UpstreamDataCorruptedError, ServerError)


def test_invalid_schema_error_is_server_error() -> None:
    assert issubclass(InvalidSchemaError, ServerError)


def test_http_error_is_server_error() -> None:
    assert issubclass(PolarsBaseballHttpError, ServerError)


def test_invalid_parameter_error_is_value_error() -> None:
    assert issubclass(InvalidParameterError, ValueError)


def test_upstream_parse_error_is_runtime_error() -> None:
    assert issubclass(UpstreamParseError, RuntimeError)


def test_upstream_structure_changed_error_is_runtime_error() -> None:
    assert issubclass(UpstreamStructureChangedError, RuntimeError)


def test_upstream_data_corrupted_error_is_runtime_error() -> None:
    assert issubclass(UpstreamDataCorruptedError, RuntimeError)


def test_all_domain_errors_catchable_as_base() -> None:
    """Ensure all domain exceptions are catchable using PolarsBaseballError."""
    errors = [
        ClientError("c"),
        ServerError("s"),
        InvalidParameterError("ip"),
        UpstreamParseError("up"),
        UpstreamStructureChangedError("usc"),
        UpstreamDataCorruptedError("udc"),
        InvalidSchemaError("is"),
        PolarsBaseballHttpError("http"),
    ]
    for err in errors:
        assert isinstance(err, PolarsBaseballError), f"{type(err)} not catchable as PolarsBaseballError"


# ── Statcast error-row raises UpstreamParseError ─────────────────────────────


@pytest.mark.asyncio
async def test_statcast_error_row_raises_upstream_parse_error() -> None:
    from datetime import date

    from polars_baseball.apis.statcast import _small_request

    async def _get_or_fetch(key: str, fetcher: object, **kwargs: object) -> pl.DataFrame:
        return await fetcher()  # type: ignore[misc]

    mock_cache = MagicMock()
    mock_cache.get.return_value = None
    mock_cache.get_or_fetch = AsyncMock(side_effect=_get_or_fetch)

    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text.return_value = "error\nsome upstream error message\n"
    ctx = BaseballContext(http=mock_http, cache=mock_cache)

    with pytest.raises(UpstreamParseError):
        await _small_request(date(2024, 4, 1), date(2024, 4, 7), context=ctx)


# ── Savant leaderboard error-row raises UpstreamParseError ───────────────────


@pytest.mark.asyncio
async def test_savant_leaderboard_error_row_raises_upstream_parse_error() -> None:
    from polars_baseball.gateways.savant import SavantGateway

    async def _get_or_fetch(key: str, fetcher: object, **kwargs: object) -> pl.DataFrame:
        return await fetcher()  # type: ignore[misc]

    mock_cache = MagicMock()
    mock_cache.get.return_value = None
    mock_cache.get_or_fetch = AsyncMock(side_effect=_get_or_fetch)

    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text.return_value = "error\nsome leaderboard error\n"
    ctx = BaseballContext(http=mock_http, cache=mock_cache)

    with pytest.raises(UpstreamParseError):
        await SavantGateway(ctx).get_leaderboard("http://dummy")


@pytest.mark.asyncio
async def test_savant_gateway_recovers_from_corrupt_cache_file(tmp_path: Path) -> None:
    """When a corrupt cache file is encountered during get_dataset, it should delete the file and fetch fresh data."""
    from polars_baseball._cache import generate_cache_key
    from polars_baseball.gateways.savant import SavantGateway

    cache = FileCacheAdapter(cache_dir=tmp_path)
    url = "https://baseballsavant.mlb.com/dummy-dataset"
    params = {"game_date": "2026-06-01"}
    key = generate_cache_key(url, params)

    corrupt_file = cache._get_path(key)
    corrupt_file.write_text("not a valid parquet content")

    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text.return_value = "game_date,game_pk\n2026-06-01,123\n"

    ctx = BaseballContext(http=mock_http, cache=cache)
    gateway = SavantGateway(ctx)

    df = await gateway.get_dataset(url, params=params)

    assert isinstance(df, pl.DataFrame)
    assert df.height == 1
    assert df["game_pk"][0] == 123

    assert corrupt_file.exists()
    assert pl.read_parquet(corrupt_file).equals(df)
    mock_http.get_text.assert_awaited_once()


def test_validate_and_cast_schema_empty_df_missing_columns() -> None:
    from polars_baseball._schema_utils import validate_and_cast_schema

    empty_df = pl.DataFrame()
    with pytest.raises(InvalidSchemaError, match="Missing required columns"):
        validate_and_cast_schema(empty_df, ["gamePk"], {"gamePk": pl.Int64})
