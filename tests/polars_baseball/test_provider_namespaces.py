import inspect

import polars_baseball as pb
from polars_baseball import BaseballClient


def test_provider_namespaces_exist() -> None:
    assert hasattr(pb, "lahman")
    assert hasattr(pb, "retrosheet")
    assert hasattr(pb, "bref")
    assert hasattr(pb, "savant")
    assert hasattr(pb, "mlb")
    assert hasattr(pb, "fangraphs")


def test_client_subclients_exist() -> None:
    client = BaseballClient()
    assert hasattr(client, "lahman")
    assert hasattr(client, "retrosheet")
    assert hasattr(client, "bref")
    assert hasattr(client, "savant")
    assert hasattr(client, "mlb")
    assert hasattr(client, "fangraphs")
    assert hasattr(client, "lookup")


def test_lahman_namespace_exports() -> None:
    client = BaseballClient()
    assert hasattr(client.lahman, "batting")
    assert hasattr(client.lahman, "pitching")
    assert hasattr(client.lahman, "fielding")
    assert hasattr(client.lahman, "people")
    assert inspect.iscoroutinefunction(client.lahman.batting)


def test_retrosheet_namespace_exports() -> None:
    client = BaseballClient()
    assert hasattr(client.retrosheet, "events")
    assert hasattr(client.retrosheet, "schedules")
    assert hasattr(client.retrosheet, "rosters")
    assert inspect.iscoroutinefunction(client.retrosheet.events)


def test_bref_namespace_exports() -> None:
    client = BaseballClient()
    assert hasattr(client.bref, "bwar_bat")
    assert hasattr(client.bref, "bwar_pitch")
    assert hasattr(client.bref, "game_logs")
    assert hasattr(client.bref, "splits")
    assert inspect.iscoroutinefunction(client.bref.bwar_bat)
    assert inspect.iscoroutinefunction(client.bref.game_logs)
    assert inspect.iscoroutinefunction(client.bref.splits)
