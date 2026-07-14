from collections.abc import Mapping
from typing import TypeAlias, cast

import polars as pl

from polars_baseball.exceptions import UpstreamParseError

JsonValue: TypeAlias = None | bool | int | float | str | list["JsonValue"] | dict[str, "JsonValue"]
JsonObject: TypeAlias = dict[str, JsonValue]
PitchRow: TypeAlias = tuple[int | None, JsonObject]

EXIT_VELOCITY_SCHEMA: Mapping[str, pl.DataType | type[pl.DataType]] = {
    "game_pk": pl.Int64,
    "batter_name": pl.String,
    "team_batting": pl.String,
    "pitcher_name": pl.String,
    "team_fielding": pl.String,
    "events": pl.String,
    "launch_speed": pl.Float64,
    "launch_angle": pl.Float64,
    "hit_distance": pl.Float64,
    "xba": pl.Float64,
    "start_speed": pl.Float64,
    "home_run_ballparks": pl.Int64,
}

PITCH_DATA_SCHEMA: Mapping[str, pl.DataType | type[pl.DataType]] = {
    "game_pk": pl.Int64,
    "pitcher_id": pl.Int64,
    "pitcher_name": pl.String,
    "team_pitching": pl.String,
    "batter_name": pl.String,
    "team_batting": pl.String,
    "pitch_name": pl.String,
    "pitch_type": pl.String,
    "description": pl.String,
    "events": pl.String,
    "start_speed": pl.Float64,
    "spin_rate": pl.Int64,
    "break_x_inches": pl.Float64,
    "break_z_induced_inches": pl.Float64,
}

_EXIT_VELOCITY_NODE = "exit_velocity"
_HOME_PITCHERS_NODE = "home_pitchers"
_AWAY_PITCHERS_NODE = "away_pitchers"
_CONTEXT_METRICS_KEY = "contextMetrics"
_HOME_RUN_BALLPARKS_KEY = "homeRunBallparks"
_BREAK_X_KEY = "breakXInches"
_BREAK_Z_KEYS = ("breakZInducedInches", "inducedBreakZ")
_PITCHER_ID_KEYS = ("pitcher_id", "pitcher", "player_id")
_NESTED_PITCHER_KEYS = ("pitcher", "player")
_NESTED_ID_KEY = "id"


class SavantGamefeedParser:
    def parse_exit_velocity(self, game_pk: int, payload: JsonObject) -> pl.DataFrame:
        rows = [self._exit_velocity_row(game_pk, item) for item in _node_rows(payload, _EXIT_VELOCITY_NODE)]
        return _frame(rows, EXIT_VELOCITY_SCHEMA)

    def parse_pitch_data(self, game_pk: int, payload: JsonObject) -> pl.DataFrame:
        rows: list[dict[str, object]] = []
        for node in (_HOME_PITCHERS_NODE, _AWAY_PITCHERS_NODE):
            rows.extend(
                self._pitch_row(game_pk, pitcher_id, item) for pitcher_id, item in _pitch_node_rows(payload, node)
            )
        return _frame(rows, PITCH_DATA_SCHEMA)

    @staticmethod
    def _exit_velocity_row(game_pk: int, item: JsonObject) -> dict[str, object]:
        context_metrics = _object_or_empty(item.get(_CONTEXT_METRICS_KEY))
        return {
            "game_pk": game_pk,
            "batter_name": _string_or_none(item.get("batter_name")),
            "team_batting": _string_or_none(item.get("team_batting")),
            "pitcher_name": _string_or_none(item.get("pitcher_name")),
            "team_fielding": _string_or_none(item.get("team_fielding")),
            "events": _string_or_none(item.get("events")),
            "launch_speed": _float_or_none(item.get("launch_speed")),
            "launch_angle": _float_or_none(item.get("launch_angle")),
            "hit_distance": _float_or_none(item.get("hit_distance")),
            "xba": _float_or_none(item.get("xba")),
            "start_speed": _float_or_none(item.get("start_speed")),
            "home_run_ballparks": _int_or_none(context_metrics.get(_HOME_RUN_BALLPARKS_KEY)),
        }

    @staticmethod
    def _pitch_row(game_pk: int, pitcher_id: int | None, item: JsonObject) -> dict[str, object]:
        return {
            "game_pk": game_pk,
            "pitcher_id": pitcher_id if pitcher_id is not None else _pitcher_id_from_row(item),
            "pitcher_name": _string_or_none(item.get("pitcher_name")),
            "team_pitching": _string_or_none(item.get("team_pitching")),
            "batter_name": _string_or_none(item.get("batter_name")),
            "team_batting": _string_or_none(item.get("team_batting")),
            "pitch_name": _string_or_none(item.get("pitch_name")),
            "pitch_type": _string_or_none(item.get("pitch_type")),
            "description": _string_or_none(item.get("description")),
            "events": _string_or_none(item.get("events")),
            "start_speed": _float_or_none(item.get("start_speed")),
            "spin_rate": _int_or_none(item.get("spin_rate")),
            "break_x_inches": _float_or_none(item.get(_BREAK_X_KEY)),
            "break_z_induced_inches": _float_or_none(_first_present(item, _BREAK_Z_KEYS)),
        }


def _pitch_node_rows(payload: JsonObject, node: str) -> list[PitchRow]:
    raw_rows = payload.get(node)
    if raw_rows is None:
        return []
    if isinstance(raw_rows, list):
        return [(None, row) for row in _list_rows(raw_rows, node)]
    if isinstance(raw_rows, dict):
        return _mapped_pitch_rows(cast(JsonObject, raw_rows), node)
    raise UpstreamParseError(f"Savant gamefeed node {node!r} must be a list or object of lists.")


def _mapped_pitch_rows(raw_map: JsonObject, node: str) -> list[PitchRow]:
    rows: list[PitchRow] = []
    for key, raw_rows in raw_map.items():
        if not isinstance(raw_rows, list):
            raise UpstreamParseError(f"Savant gamefeed node {node!r} key {key!r} must contain a list.")
        pitcher_id = _int_or_none(key)
        rows.extend((pitcher_id, row) for row in _list_rows(raw_rows, node))
    return rows


def _node_rows(payload: JsonObject, node: str) -> list[JsonObject]:
    raw_rows = payload.get(node)
    if raw_rows is None:
        return []
    if isinstance(raw_rows, list):
        return _list_rows(raw_rows, node)
    if isinstance(raw_rows, dict):
        return _mapped_list_rows(cast(JsonObject, raw_rows), node)
    raise UpstreamParseError(f"Savant gamefeed node {node!r} must be a list or object of lists.")


def _list_rows(raw_rows: list[JsonValue], node: str) -> list[JsonObject]:
    rows: list[JsonObject] = []
    for raw_row in raw_rows:
        if not isinstance(raw_row, dict):
            raise UpstreamParseError(f"Savant gamefeed node {node!r} contains a non-object row.")
        rows.append(cast(JsonObject, raw_row))
    return rows


def _mapped_list_rows(raw_map: JsonObject, node: str) -> list[JsonObject]:
    rows: list[JsonObject] = []
    for key, raw_rows in raw_map.items():
        if not isinstance(raw_rows, list):
            raise UpstreamParseError(f"Savant gamefeed node {node!r} key {key!r} must contain a list.")
        rows.extend(_list_rows(raw_rows, node))
    return rows


def _pitcher_id_from_row(item: JsonObject) -> int | None:
    for key in _PITCHER_ID_KEYS:
        value = item.get(key)
        if isinstance(value, dict):
            continue
        pitcher_id = _int_or_none(value)
        if pitcher_id is not None:
            return pitcher_id
    for key in _NESTED_PITCHER_KEYS:
        value = item.get(key)
        if not isinstance(value, dict):
            continue
        pitcher_id = _int_or_none(value.get(_NESTED_ID_KEY))
        if pitcher_id is not None:
            return pitcher_id
    return None


def _frame(rows: list[dict[str, object]], schema: Mapping[str, pl.DataType | type[pl.DataType]]) -> pl.DataFrame:
    if not rows:
        return pl.DataFrame(schema=schema)
    return pl.DataFrame(rows, schema=schema)


def _object_or_empty(value: JsonValue) -> JsonObject:
    if isinstance(value, dict):
        return cast(JsonObject, value)
    return {}


def _string_or_none(value: JsonValue) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value.strip()
    return str(value)


def _float_or_none(value: JsonValue) -> float | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int | float):
        return float(value)
    if isinstance(value, str) and value.strip():
        return float(value)
    return None


def _int_or_none(value: JsonValue) -> int | None:
    if value is None or isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(value)
    if isinstance(value, str) and value.strip():
        return int(float(value))
    return None


def _first_present(item: JsonObject, keys: tuple[str, ...]) -> JsonValue:
    for key in keys:
        value = item.get(key)
        if value is not None:
            return value
    return None
