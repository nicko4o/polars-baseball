"""Internal MLB team lookup helpers."""

import polars as pl

from polars_baseball._season import most_recent_season
from polars_baseball.context import BaseballContext
from polars_baseball.exceptions import InvalidParameterError

from .taxonomy import _fetch_mlb_teams

_TEAM_ID_COLUMN = "id"
_TEAM_NAME_COLUMN = "teamName"
_TEAM_NAME_STRIP_PATTERN = r"[ -]"
_UNKNOWN_TEAM_ID = -1


def _normalize_team_name_expr(column: str) -> pl.Expr:
    return pl.col(column).str.to_lowercase().str.replace_all(_TEAM_NAME_STRIP_PATTERN, "")


def _normalize_team_name(team_name: str) -> str:
    return team_name.replace(" ", "").replace("-", "").lower()


async def resolve_team_id(team_name: str, context: BaseballContext | None = None) -> int:
    """Resolve an MLB team display name to a Stats API team id."""
    team_name_clean = _normalize_team_name(team_name)
    teams_df = await _fetch_mlb_teams(season=most_recent_season(), context=context)
    filtered = teams_df.filter(_normalize_team_name_expr(_TEAM_NAME_COLUMN) == team_name_clean)

    if filtered.is_empty():
        raise InvalidParameterError(f"Could not resolve team name: {team_name}")

    team_id = filtered[_TEAM_ID_COLUMN][0]
    if team_id is None or team_id == _UNKNOWN_TEAM_ID:
        raise InvalidParameterError(f"Could not resolve team name: {team_name}")
    return int(team_id)
