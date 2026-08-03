import inspect

import polars_baseball as pb

ROOT_PUBLIC_API = {
    "ArsenalType",
    "BaseballContext",
    "FanGraphsFilter",
    "FanGraphsFilterOp",
    "FanGraphsRequest",
    "FangraphsLeague",
    "FangraphsMonth",
    "FangraphsPositions",
    "FangraphsStatColumn",
    "FangraphsStatsCategory",
    "KeyType",
    "MlbRosterType",
    "MlbStatsGroup",
    "Position",
    "bref",
    "chadwick_register",
    "cleanup",
    "configure_cache",
    "fangraphs",
    "fg_data",
    "get_lookup_table",
    "lahman",
    "mlb",
    "player_name_suggestions",
    "player_search_list",
    "playerid_lookup",
    "playerid_reverse_lookup",
    "prospect_rankings",
    "retrosheet",
    "savant",
    "standings",
    "statcast",
    "statcast_batter",
    "statcast_pitcher",
    "statcast_single_game",
    "team_ids",
    "top_prospects",
}

IMPLEMENTATION_NAMESPACE_LEAKS = {
    "apis",
    "context",
    "enums",
    "exceptions",
    "gateways",
    "logging",
    "parsers",
}


def test_public_api_symbols_exist() -> None:
    public_symbols = {name for name in dir(pb) if not name.startswith("_")}
    missing = ROOT_PUBLIC_API - public_symbols
    assert not missing, f"Missing public symbols: {missing}"


def test_root_all_is_stable_public_api() -> None:
    assert set(pb.__all__) == ROOT_PUBLIC_API


def test_root_namespace_hides_implementation_packages() -> None:
    public_symbols = {name for name in dir(pb) if not name.startswith("_")}
    leaks = public_symbols & IMPLEMENTATION_NAMESPACE_LEAKS
    assert not leaks, f"Implementation namespaces leaked at package root: {leaks}"


def test_root_namespace_has_no_unlisted_user_facing_symbols() -> None:
    public_symbols = {name for name in dir(pb) if not name.startswith("_")}
    extra_ok = public_symbols - ROOT_PUBLIC_API
    missing = ROOT_PUBLIC_API - public_symbols
    assert not missing, f"Missing public symbols: {missing}"
    assert not extra_ok, f"Unexpected symbols in public namespace: {extra_ok}"


def test_statcast_is_async_function() -> None:
    assert inspect.iscoroutinefunction(pb.statcast)


def test_cleanup_is_async_function() -> None:
    assert inspect.iscoroutinefunction(pb.cleanup)


def test_provider_namespace_functions_are_async() -> None:
    assert inspect.iscoroutinefunction(pb.mlb.schedule)
    assert inspect.iscoroutinefunction(pb.mlb.game_boxscore)
    assert inspect.iscoroutinefunction(pb.savant.statcast)
    assert inspect.iscoroutinefunction(pb.savant.gamefeed_pitch_data)
    assert inspect.iscoroutinefunction(pb.savant.arm_strength)
    assert inspect.iscoroutinefunction(pb.lahman.batting)
    assert inspect.iscoroutinefunction(pb.retrosheet.events)
    assert inspect.iscoroutinefunction(pb.bref.bwar_bat)


def test_root_public_api_has_docstrings() -> None:
    missing_docstrings = [
        name
        for name in pb.__all__
        if (inspect.isfunction(getattr(pb, name)) or inspect.isclass(getattr(pb, name)))
        and not inspect.getdoc(getattr(pb, name))
    ]

    assert not missing_docstrings, f"Root public API missing docstrings: {missing_docstrings}"


def test_root_public_api_docstrings_do_not_use_numpy_sections() -> None:
    numpy_style_docstrings = []
    for name in pb.__all__:
        doc = inspect.getdoc(getattr(pb, name))
        if doc is not None and "----------" in doc:
            numpy_style_docstrings.append(name)

    assert not numpy_style_docstrings, f"Root public API docstrings use NumPy-style sections: {numpy_style_docstrings}"
