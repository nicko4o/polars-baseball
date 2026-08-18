import json
from collections.abc import Callable

import polars as pl

from polars_baseball._config import FILM_ROOM_GRAPHQL_URL, FILM_ROOM_SEARCH_URL, MLB_ROOT
from polars_baseball.context import BaseballContext
from polars_baseball.exceptions import UpstreamParseError

PAGE_SIZE = 20

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
        dfs: list[pl.DataFrame] = []
        remaining = limit

        for page in range(1, num_pages + 1):
            fetch_limit = min(remaining, PAGE_SIZE)
            raw_payload = await self._fetch_page(query_str, limit=fetch_limit, page=page, error_msg=error_msg)
            df = self._parse(raw_payload, f"{error_msg} (page {page})", parser)
            if df.is_empty():
                break
            dfs.append(df)
            if len(df) < fetch_limit:
                break
            remaining -= len(df)
            if remaining <= 0:
                break

        if not dfs:
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
            "Origin": MLB_ROOT,
            "Referer": FILM_ROOM_SEARCH_URL,
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
