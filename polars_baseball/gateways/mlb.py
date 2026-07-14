import json
from collections.abc import Callable, Mapping
from typing import cast

import polars as pl

from polars_baseball._json_types import JsonObject
from polars_baseball.context import BaseballContext
from polars_baseball.exceptions import PolarsBaseballHttpError, UpstreamParseError


class MlbStatsGateway:
    """Gateway for MLB Stats API JSON payloads."""

    def __init__(self, context: BaseballContext) -> None:
        self._context = context

    async def fetch(
        self,
        url: str,
        params: Mapping[str, object] | None,
        error_msg: str,
        parser: Callable[[JsonObject], pl.DataFrame],
    ) -> pl.DataFrame:
        try:
            raw_text = await self._context.http.get_text(url, params=params)
        except PolarsBaseballHttpError:
            raise
        except Exception as exc:
            raise UpstreamParseError(f"{error_msg}: {exc}") from exc

        try:
            result = json.loads(raw_text)
        except Exception as exc:
            raise UpstreamParseError(f"{error_msg}: {exc}") from exc

        if not isinstance(result, dict):
            raise UpstreamParseError(f"Expected dict from API response, got {type(result)}")

        try:
            return parser(cast(JsonObject, result))
        except Exception as exc:
            raise UpstreamParseError(f"{error_msg}: {exc}") from exc
