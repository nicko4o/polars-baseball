import inspect

import polars_baseball as pb


def test_provider_namespaces_exist() -> None:
    assert hasattr(pb, "lahman")
    assert hasattr(pb, "retrosheet")
    assert hasattr(pb, "bref")
    assert hasattr(pb, "savant")
    assert hasattr(pb, "mlb")
    assert hasattr(pb, "fangraphs")


def test_lahman_namespace_exports() -> None:
    assert hasattr(pb.lahman, "batting")
    assert hasattr(pb.lahman, "pitching")
    assert hasattr(pb.lahman, "fielding")
    assert hasattr(pb.lahman, "people")
    assert inspect.iscoroutinefunction(pb.lahman.batting)


def test_retrosheet_namespace_exports() -> None:
    assert hasattr(pb.retrosheet, "events")
    assert hasattr(pb.retrosheet, "schedules")
    assert hasattr(pb.retrosheet, "rosters")
    assert inspect.iscoroutinefunction(pb.retrosheet.events)


def test_bref_namespace_exports() -> None:
    assert hasattr(pb.bref, "bwar_bat")
    assert hasattr(pb.bref, "bwar_pitch")
    assert inspect.iscoroutinefunction(pb.bref.bwar_bat)
