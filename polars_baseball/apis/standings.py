import json
from collections.abc import Mapping

import polars as pl

from polars_baseball._cache import cached_list, generate_cache_key
from polars_baseball._config import MLB_FIRST_YEAR, STATS_API_ROOT
from polars_baseball._schema_utils import validate_and_cast_schema
from polars_baseball._season import most_recent_season
from polars_baseball.context import BaseballContext, default_context
from polars_baseball.exceptions import InvalidParameterError, UpstreamParseError

# Standings schema
STANDINGS_REQUIRED: list[str] = ["Tm", "W", "L"]
STANDINGS_TYPES: dict[str, pl.DataType | type[pl.DataType]] = {
    "teamId": pl.Int64,
    "Tm": pl.String,
    "W": pl.Int64,
    "L": pl.Int64,
    "W-L%": pl.Float64,
    "GB": pl.Float64,
}

_STANDINGS_GB_NULL_VALUES: frozenset[str] = frozenset({"--", "-", "Tied"})
_PRE_DEAD_BALL_START = MLB_FIRST_YEAR


def _parse_team_record(rec: Mapping[str, object]) -> dict[str, object]:
    team = rec.get("team")
    team_name = team.get("name") if isinstance(team, Mapping) else None
    team_id = team.get("id") if isinstance(team, Mapping) else None

    league_record = rec.get("leagueRecord")
    wins = None
    losses = None
    pct_str = None
    if isinstance(league_record, Mapping):
        wins = league_record.get("wins")
        losses = league_record.get("losses")
        pct_str = league_record.get("pct")

    pct = None
    if isinstance(pct_str, (str, float, int)):
        try:
            pct = float(pct_str)
        except ValueError:
            pass

    gb_str = rec.get("gamesBack")
    gb = None
    if isinstance(gb_str, (str, float, int)) and str(gb_str) not in _STANDINGS_GB_NULL_VALUES:
        try:
            gb = float(gb_str)
        except ValueError:
            pass

    return {
        "teamId": team_id,
        "Tm": team_name,
        "W": wins,
        "L": losses,
        "W-L%": pct,
        "GB": gb,
    }


def _parse_division_records(division_record: Mapping[str, object]) -> pl.DataFrame:
    team_records = division_record.get("teamRecords")
    parsed_records = []
    if isinstance(team_records, list):
        for r in team_records:
            if isinstance(r, Mapping):
                typed_r = {str(k): v for k, v in r.items()}
                parsed_records.append(_parse_team_record(typed_r))

    if not parsed_records:
        return pl.DataFrame(schema=STANDINGS_TYPES)

    df = pl.DataFrame(parsed_records, schema=STANDINGS_TYPES)
    return validate_and_cast_schema(df, STANDINGS_REQUIRED, STANDINGS_TYPES)


def _standings_cache_key(season: int) -> str:
    url = f"{STATS_API_ROOT}/standings?leagueId=103,104&season={season}"
    return generate_cache_key(url, {})


@cached_list(key=_standings_cache_key)
async def _fetch_standings(season: int, context: BaseballContext | None = None) -> list[pl.DataFrame]:
    ctx = context or default_context()
    url = f"{STATS_API_ROOT}/standings?leagueId=103,104&season={season}"
    try:
        res = ctx.http.get_text(url)
        html = await res if not isinstance(res, str) else res
        data = json.loads(html)
    except Exception as e:
        raise UpstreamParseError(f"Failed to fetch or parse standings from MLB Stats API: {e}") from e

    records = data.get("records", [])
    return [_parse_division_records(rec) for rec in records]


async def standings(season: int | None = None, context: BaseballContext | None = None) -> list[pl.DataFrame]:
    """Fetch division standings from the MLB Stats API for a given season.

    Returns a list of DataFrames, one per division, each containing ``Tm``,
    ``W``, ``L``, ``W-L%``, and ``GB`` columns.

    Edge Cases:
        - Raises ``InvalidParameterError`` for seasons before 1901 (``MLB_FIRST_YEAR``).
        - Defaults to the most recent completed season when ``season`` is omitted.
        - Games Back (``GB``) is ``None`` for division leaders or tied values.
    """
    if season is None:
        season = most_recent_season()
    if season < _PRE_DEAD_BALL_START:
        raise InvalidParameterError(
            f"This query currently only returns standings until the {_PRE_DEAD_BALL_START} season. "
            f"Try looking at years from {_PRE_DEAD_BALL_START} to present."
        )
    return await _fetch_standings(season, context=context)
