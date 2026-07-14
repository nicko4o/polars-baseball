import inspect

import polars_baseball as pb

ROOT_PUBLIC_API = {
    "ArsenalType",
    "BaseballContext",
    "FanGraphsRequest",
    "KeyType",
    "cleanup",
    "configure_cache",
    "fg_data",
    "mlb_divisions",
    "mlb_draft",
    "mlb_game_boxscore",
    "mlb_game_boxscore_stats",
    "mlb_game_feed_live",
    "mlb_game_linescore",
    "mlb_game_play_by_play",
    "mlb_game_win_probability",
    "mlb_leagues",
    "mlb_people",
    "mlb_people_awards",
    "mlb_pitch_arsenal",
    "mlb_player_stats",
    "mlb_postseason_schedule",
    "mlb_roster",
    "mlb_schedule",
    "mlb_stat_leaders",
    "mlb_team_stats",
    "mlb_teams",
    "mlb_transactions",
    "mlb_venues",
    "playerid_lookup",
    "prospect_rankings",
    "savant_gamefeed_exit_velocity",
    "savant_gamefeed_exit_velocity_many",
    "savant_gamefeed_pitch_data",
    "savant_gamefeed_pitch_data_many",
    "standings",
    "statcast",
    "statcast_arm_strength",
    "statcast_baserunning_run_value",
    "statcast_catcher_stance",
    "statcast_catcher_throwing",
    "statcast_batter",
    "statcast_pitcher",
    "statcast_single_game",
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
    assert public_symbols == ROOT_PUBLIC_API, (
        f"Unexpected symbols in public namespace: {public_symbols - ROOT_PUBLIC_API}"
    )


def test_statcast_is_async_function() -> None:
    assert inspect.iscoroutinefunction(pb.statcast)


def test_cleanup_is_async_function() -> None:
    assert inspect.iscoroutinefunction(pb.cleanup)


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
