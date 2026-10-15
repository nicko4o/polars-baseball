from unittest.mock import AsyncMock

import polars as pl
import pytest

from polars_baseball._client import HttpClient
from polars_baseball.client import BaseballClient, BaseballContext
from polars_baseball.exceptions import InvalidParameterError

_default_client = BaseballClient()


async def statcast_base_stealing(
    *args: object, context: BaseballClient | None = None, client: BaseballClient | None = None, **kwargs: object
) -> pl.DataFrame:
    c = client or context or _default_client
    return await c.savant.base_stealing(*args, **kwargs)  # type: ignore[arg-type]


async def statcast_catcher_blocking(
    *args: object, context: BaseballClient | None = None, client: BaseballClient | None = None, **kwargs: object
) -> pl.DataFrame:
    c = client or context or _default_client
    return await c.savant.catcher_blocking(*args, **kwargs)  # type: ignore[arg-type]


async def statcast_catcher_framing(
    *args: object, context: BaseballClient | None = None, client: BaseballClient | None = None, **kwargs: object
) -> pl.DataFrame:
    c = client or context or _default_client
    return await c.savant.catcher_framing(*args, **kwargs)  # type: ignore[arg-type]


async def statcast_catcher_poptime(
    *args: object, context: BaseballClient | None = None, client: BaseballClient | None = None, **kwargs: object
) -> pl.DataFrame:
    c = client or context or _default_client
    return await c.savant.catcher_poptime(*args, **kwargs)  # type: ignore[arg-type]


async def statcast_fielding_run_value(
    *args: object, context: BaseballClient | None = None, client: BaseballClient | None = None, **kwargs: object
) -> pl.DataFrame:
    c = client or context or _default_client
    return await c.savant.fielding_run_value(*args, **kwargs)  # type: ignore[arg-type]


async def statcast_outfield_catch_prob(
    *args: object, context: BaseballClient | None = None, client: BaseballClient | None = None, **kwargs: object
) -> pl.DataFrame:
    c = client or context or _default_client
    return await c.savant.outfield_catch_prob(*args, **kwargs)  # type: ignore[arg-type]


async def statcast_outfield_directional_oaa(
    *args: object, context: BaseballClient | None = None, client: BaseballClient | None = None, **kwargs: object
) -> pl.DataFrame:
    c = client or context or _default_client
    return await c.savant.outfield_directional_oaa(*args, **kwargs)  # type: ignore[arg-type]


async def statcast_outfielder_jump(
    *args: object, context: BaseballClient | None = None, client: BaseballClient | None = None, **kwargs: object
) -> pl.DataFrame:
    c = client or context or _default_client
    return await c.savant.outfielder_jump(*args, **kwargs)  # type: ignore[arg-type]


async def statcast_outs_above_average(
    *args: object, context: BaseballClient | None = None, client: BaseballClient | None = None, **kwargs: object
) -> pl.DataFrame:
    c = client or context or _default_client
    return await c.savant.outs_above_average(*args, **kwargs)  # type: ignore[arg-type]


async def statcast_running_splits(
    *args: object, context: BaseballClient | None = None, client: BaseballClient | None = None, **kwargs: object
) -> pl.DataFrame:
    c = client or context or _default_client
    return await c.savant.running_splits(*args, **kwargs)  # type: ignore[arg-type]


async def statcast_sprint_speed(
    *args: object, context: BaseballClient | None = None, client: BaseballClient | None = None, **kwargs: object
) -> pl.DataFrame:
    c = client or context or _default_client
    return await c.savant.sprint_speed(*args, **kwargs)  # type: ignore[arg-type]


@pytest.fixture
def mock_csv_data() -> bytes:
    return b"name,player_id,year,value\nOhtani Shohei,660271,2026,10.0\nTrout Mike,545361,2026,9.5\n"


@pytest.mark.asyncio
async def test_running_apis(mock_csv_data: bytes) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=mock_csv_data)
    ctx = BaseballContext(http=mock_http)

    df1 = await statcast_sprint_speed(2026, context=ctx)
    assert isinstance(df1, pl.DataFrame)
    assert df1.height == 2

    df2 = await statcast_running_splits(2026, context=ctx)
    assert df2.height == 2


@pytest.mark.asyncio
async def test_fielding_apis(mock_csv_data: bytes) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=mock_csv_data)
    ctx = BaseballContext(http=mock_http)

    df1 = await statcast_outs_above_average(2026, pos=3, context=ctx)
    assert df1.height == 2

    with pytest.raises(InvalidParameterError, match="This particular leaderboard does not include catchers"):
        await statcast_outs_above_average(2026, pos=2, context=ctx)

    df2 = await statcast_fielding_run_value(2026, pos=3, context=ctx)
    assert df2.height == 2

    df3 = await statcast_outfield_directional_oaa(2026, context=ctx)
    assert df3.height == 2

    df4 = await statcast_outfield_catch_prob(2026, context=ctx)
    assert df4.height == 2

    df5 = await statcast_outfielder_jump(2026, context=ctx)
    assert df5.height == 2

    df6 = await statcast_catcher_poptime(2026, context=ctx)
    assert df6.height == 2


@pytest.mark.asyncio
async def test_oaa_fallback_on_html_response() -> None:
    html_data = b"""<!DOCTYPE html>
<html><head><title>Statcast Outs Above Average Leaderboard</title></head>
<body><div class="leaderboard-container">
<table id="leaderboard_table">
<thead><tr><th>player_id</th><th>player_name</th><th>team</th><th>pos</th><th>oaa</th><th>season</th></tr></thead>
<tbody>
<tr><td>660271</td><td><a href="/player/660271">Ohtani, Shohei</a></td><td>LAA</td><td>CF</td><td>10</td><td>2023</td></tr>
<tr><td>545361</td><td><a href="/player/545361">Trout, Mike</a></td><td>LAA</td><td>CF</td><td>8</td><td>2023</td></tr>
</tbody></table></div></body></html>"""
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=html_data)
    ctx = BaseballContext(http=mock_http)

    df = await statcast_outs_above_average(2023, pos="CF", context=ctx)
    assert isinstance(df, pl.DataFrame)
    assert df.height == 2
    assert "player_id" in df.columns
    assert "player_name" in df.columns


@pytest.mark.asyncio
async def test_oaa_rejects_aggregate_pos() -> None:
    """Aggregate position codes (IF, OF, ALL) must raise InvalidParameterError."""
    with pytest.raises(InvalidParameterError, match="aggregate code"):
        await statcast_outs_above_average(2023, pos="OF")

    with pytest.raises(InvalidParameterError, match="aggregate code"):
        await statcast_outs_above_average(2023, pos="IF")


@pytest.mark.asyncio
async def test_catcher_framing_filtering() -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=b"name,player_id,year,rv_tot\nRealmuto J.T.,592663,2026,10\n,,2026,0\n")
    ctx = BaseballContext(http=mock_http)

    df = await statcast_catcher_framing(2026, context=ctx)
    assert df.height == 1
    assert df["player_id"][0] == 592663


@pytest.mark.asyncio
async def test_catcher_blocking_and_base_stealing(mock_csv_data: bytes) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=mock_csv_data)
    ctx = BaseballContext(http=mock_http)

    df_blocking = await statcast_catcher_blocking(2026, context=ctx)
    assert isinstance(df_blocking, pl.DataFrame)
    assert df_blocking.height == 2

    df_stealing = await statcast_base_stealing(2026, context=ctx)
    assert isinstance(df_stealing, pl.DataFrame)
    assert df_stealing.height == 2
