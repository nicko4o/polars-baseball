"""MLB Stats API parser for venue data."""

from typing import cast

import polars as pl

from polars_baseball._json_utils import JsonObject
from polars_baseball._schema_utils import validate_and_cast_schema
from polars_baseball._schemas.mlb import MLB_VENUES_REQUIRED, MLB_VENUES_TYPES
from polars_baseball.parsers.mlb.types import VenueDict


def parse_venue(venue: JsonObject) -> VenueDict:
    return cast(
        VenueDict,
        {
            "id": venue.get("id"),
            "name": venue.get("name"),
            "link": venue.get("link"),
            "active": venue.get("active"),
            "season": venue.get("season"),
        },
    )


def parse_mlb_venues(data: JsonObject) -> pl.DataFrame:
    """Parse venues from MLB Stats API /venues response.

    Extracts id, name, link, active, and season from each venue in the
    venues array.
    """
    venues = data.get("venues", [])
    if not isinstance(venues, list) or not venues:
        return pl.DataFrame()
    rows = [parse_venue(cast(JsonObject, venue)) for venue in venues if isinstance(venue, dict)]
    if not rows:
        return pl.DataFrame()
    return validate_and_cast_schema(pl.DataFrame(rows, schema=MLB_VENUES_TYPES), MLB_VENUES_REQUIRED, MLB_VENUES_TYPES)
