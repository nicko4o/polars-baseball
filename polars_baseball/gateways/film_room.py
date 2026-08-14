import asyncio
import json
from collections.abc import Callable

import polars as pl

from polars_baseball._config import FILM_ROOM_GRAPHQL_URL
from polars_baseball.context import BaseballContext
from polars_baseball.exceptions import UpstreamParseError

PAGE_SIZE = 100
MAX_CONCURRENCY = 5

SEARCH_GRAPHQL_QUERY = """
query FilmRoomSearch($query: String!, $limit: Int, $page: Int) {
  search(query: $query, limit: $limit, page: $page) {
    total
    plays {
      id
      gamePk
      gameDate
      fields {
        name
        value
        displayValue
      }
      mediaPlayback {
        id
        title
        blurb
        description
        date
        mediaPlaybackId
      }
    }
  }
}
"""


class FilmRoomGateway:
    """Gateway for querying MLB Film Room GraphQL and REST services."""

    def __init__(self, context: BaseballContext) -> None:
        self._context = context

    async def fetch_search(
        self,
        query_str: str,
        limit: int,
        error_msg: str,
        parser: Callable[[object], pl.DataFrame],
    ) -> pl.DataFrame:
        if limit <= 0:
            raise ValueError(f"limit must be positive, got {limit}")

        num_pages = (limit + PAGE_SIZE - 1) // PAGE_SIZE

        if num_pages == 1:
            raw_payload = await self._fetch_page(query_str, limit=limit, page=1, error_msg=error_msg)
            return self._parse(raw_payload, error_msg, parser)

        sem = asyncio.Semaphore(MAX_CONCURRENCY)

        async def _bounded_fetch_page(page_num: int, current_limit: int) -> object:
            async with sem:
                return await self._fetch_page(query_str, limit=current_limit, page=page_num, error_msg=error_msg)

        tasks = []
        remaining = limit
        for p in range(1, num_pages + 1):
            fetch_limit = min(remaining, PAGE_SIZE)
            tasks.append(_bounded_fetch_page(p, fetch_limit))
            remaining -= fetch_limit

        page_results = await asyncio.gather(*tasks, return_exceptions=True)

        dfs: list[pl.DataFrame] = []
        for idx, res in enumerate(page_results, start=1):
            if isinstance(res, Exception):
                raise UpstreamParseError(f"{error_msg} (page {idx}): {res}") from res
            df = self._parse(res, error_msg, parser)
            if not df.is_empty():
                dfs.append(df)

        if not dfs:
            # Return empty schema DataFrame from parser
            return parser({})

        return pl.concat(dfs)

    async def _fetch_page(self, query_str: str, limit: int, page: int, error_msg: str) -> object:
        payload = {
            "operationName": "FilmRoomSearch",
            "query": SEARCH_GRAPHQL_QUERY,
            "variables": {
                "query": query_str,
                "limit": limit,
                "page": page,
            },
        }
        headers = {
            "Content-Type": "application/json",
            "Origin": "https://www.mlb.com",
            "Referer": "https://www.mlb.com/video/search",
        }

        raw_text = await self._context.http.post_json(FILM_ROOM_GRAPHQL_URL, json_data=payload, headers=headers)

        try:
            return json.loads(raw_text)
        except json.JSONDecodeError as exc:
            raise UpstreamParseError(f"{error_msg}: {exc}") from exc

    @staticmethod
    def _parse(raw_payload: object, error_msg: str, parser: Callable[[object], pl.DataFrame]) -> pl.DataFrame:
        try:
            return parser(raw_payload)
        except (KeyError, TypeError, ValueError, pl.exceptions.PolarsError) as exc:
            raise UpstreamParseError(f"{error_msg}: {exc}") from exc
