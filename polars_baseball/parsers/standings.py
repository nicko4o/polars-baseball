from collections.abc import Mapping

import polars as pl

from polars_baseball._schema_utils import validate_and_cast_schema
from polars_baseball.exceptions import UpstreamParseError

STANDINGS_REQUIRED: list[str] = ["Tm", "W", "L"]
STANDINGS_TYPES: dict[str, pl.DataType | type[pl.DataType]] = {
    "season": pl.Int64,
    "division_id": pl.Int64,
    "division_name": pl.String,
    "teamId": pl.Int64,
    "Tm": pl.String,
    "W": pl.Int64,
    "L": pl.Int64,
    "W-L%": pl.Float64,
    "GB": pl.Float64,
}

_STANDINGS_GB_NULL_VALUES: frozenset[str] = frozenset({"--", "-", "Tied"})
_STANDINGS_PCT_LABEL = "W-L%"
_STANDINGS_GB_LABEL = "GB"


def _parse_optional_float(
    value: object,
    *,
    label: str,
    null_values: frozenset[str] = frozenset(),
) -> float | None:
    if value is None:
        return None
    if str(value) in null_values:
        return None
    if not isinstance(value, (str, float, int)):
        raise UpstreamParseError(f"Invalid standings {label} value: {value!r}")
    try:
        return float(value)
    except ValueError as exc:
        raise UpstreamParseError(f"Invalid standings {label} value: {value!r}") from exc


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

    return {
        "teamId": team_id,
        "Tm": team_name,
        "W": wins,
        "L": losses,
        _STANDINGS_PCT_LABEL: _parse_optional_float(pct_str, label=_STANDINGS_PCT_LABEL),
        _STANDINGS_GB_LABEL: _parse_optional_float(
            rec.get("gamesBack"),
            label=_STANDINGS_GB_LABEL,
            null_values=_STANDINGS_GB_NULL_VALUES,
        ),
    }


def _division_metadata(division_record: Mapping[str, object]) -> dict[str, object]:
    division = division_record.get("division")
    if not isinstance(division, Mapping):
        return {"division_id": None, "division_name": None}
    return {
        "division_id": division.get("id"),
        "division_name": division.get("name"),
    }


def _parse_division_records(division_record: Mapping[str, object], season: int) -> pl.DataFrame:
    team_records = division_record.get("teamRecords")
    metadata = _division_metadata(division_record)
    parsed_records = []
    if isinstance(team_records, list):
        for row in team_records:
            if isinstance(row, Mapping):
                typed_row = {str(k): v for k, v in row.items()}
                parsed_records.append({"season": season, **metadata, **_parse_team_record(typed_row)})

    if not parsed_records:
        return pl.DataFrame(schema=STANDINGS_TYPES)

    df = pl.DataFrame(parsed_records, schema=STANDINGS_TYPES)
    return validate_and_cast_schema(df, STANDINGS_REQUIRED, STANDINGS_TYPES)


def parse_standings_payload(payload: object, season: int) -> pl.DataFrame:
    """Parse MLB Stats API standings JSON payload into a DataFrame.

    Walks records[].teamRecords[], extracting team id, name, wins,
    losses, winning percentage, and games back. Returns one row per
    team-division-season combination.

    Note:
        Raises UpstreamParseError when the root payload is not a dict.
        Returns an empty DataFrame with STANDINGS_TYPES schema when
        no records are found.
    """
    if not isinstance(payload, Mapping):
        raise UpstreamParseError(f"Standings payload root must be object, got {type(payload)}")

    records = payload.get("records", [])
    if not isinstance(records, list):
        return pl.DataFrame(schema=STANDINGS_TYPES)

    divisions = [_parse_division_records(rec, season) for rec in records if isinstance(rec, Mapping)]
    if not divisions:
        return pl.DataFrame(schema=STANDINGS_TYPES)
    return pl.concat(divisions)
