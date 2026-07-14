from typing import Any

from polars_baseball.parsers.mlb.types import VenueDict


def parse_venue(venue: dict[str, Any]) -> VenueDict:
    return {
        "id": venue.get("id"),
        "name": venue.get("name"),
        "link": venue.get("link"),
        "active": venue.get("active"),
        "season": venue.get("season"),
    }
