import inspect

import polars_baseball as pb

ROOT_PUBLIC_API = {
    "ArsenalType",
    "BaseballContext",
    "FanGraphsRequest",
    "KeyType",
    "fg_data",
    "all_star_full",
    "all_star_game_logs",
    "appearances",
    "awards_managers",
    "awards_players",
    "awards_share_managers",
    "awards_share_players",
    "batting",
    "batting_post",
    "bwar_bat",
    "bwar_pitch",
    "chadwick_register",
    "college_playing",
    "cleanup",
    "configure_cache",
    "division_series_logs",
    "download_lahman",
    "events",
    "fielding",
    "fielding_of",
    "fielding_of_split",
    "fielding_post",
    "fangraphs",
    "get_lookup_table",
    "hall_of_fame",
    "home_games",
    "lcs_logs",
    "managers",
    "managers_half",
    "mlb",
    "park_codes",
    "parks",
    "people",
    "pitching",
    "pitching_post",
    "player_name_suggestions",
    "playerid_lookup",
    "player_search_list",
    "playerid_reverse_lookup",
    "prospect_rankings",
    "rosters",
    "salaries",
    "savant",
    "schedules",
    "schools",
    "season_game_logs",
    "series_post",
    "standings",
    "statcast",
    "statcast_batter",
    "statcast_pitcher",
    "statcast_single_game",
    "teams_core",
    "teams_franchises",
    "teams_half",
    "teams_upstream",
    "team_ids",
    "top_prospects",
    "wild_card_logs",
    "world_series_logs",
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
