import logging as _logging

from polars_baseball._cache import configure_cache
from polars_baseball.apis.bref import bwar_bat, bwar_pitch
from polars_baseball.apis.fangraphs import FanGraphsRequest, fg_data
from polars_baseball.apis.lahman import (
    all_star_full,
    appearances,
    awards_managers,
    awards_players,
    awards_share_managers,
    awards_share_players,
    batting,
    batting_post,
    college_playing,
    download_lahman,
    fielding,
    fielding_of,
    fielding_of_split,
    fielding_post,
    hall_of_fame,
    home_games,
    managers,
    managers_half,
    parks,
    people,
    pitching,
    pitching_post,
    salaries,
    schools,
    series_post,
    teams_core,
    teams_franchises,
    teams_half,
    teams_upstream,
)
from polars_baseball.apis.mlb import (
    mlb_divisions,
    mlb_draft,
    mlb_game_boxscore,
    mlb_game_boxscore_stats,
    mlb_game_feed_live,
    mlb_game_linescore,
    mlb_game_play_by_play,
    mlb_game_win_probability,
    mlb_leagues,
    mlb_people,
    mlb_people_awards,
    mlb_pitch_arsenal,
    mlb_player_stats,
    mlb_postseason_schedule,
    mlb_roster,
    mlb_schedule,
    mlb_stat_leaders,
    mlb_team_stats,
    mlb_teams,
    mlb_transactions,
    mlb_venues,
)
from polars_baseball.apis.playerid import (
    chadwick_register,
    get_lookup_table,
    player_search_list,
    playerid_lookup,
    playerid_reverse_lookup,
)
from polars_baseball.apis.retrosheet import (
    all_star_game_logs,
    division_series_logs,
    events,
    lcs_logs,
    park_codes,
    rosters,
    schedules,
    season_game_logs,
    wild_card_logs,
    world_series_logs,
)
from polars_baseball.apis.savant_fielding_running import (
    statcast_arm_strength,
    statcast_baserunning_run_value,
    statcast_catcher_stance,
    statcast_catcher_throwing,
)
from polars_baseball.apis.savant_gamefeed import (
    savant_gamefeed_exit_velocity,
    savant_gamefeed_exit_velocity_many,
    savant_gamefeed_pitch_data,
    savant_gamefeed_pitch_data_many,
)
from polars_baseball.apis.standings import standings
from polars_baseball.apis.statcast import statcast, statcast_batter, statcast_pitcher, statcast_single_game
from polars_baseball.apis.top_prospects import prospect_rankings, top_prospects
from polars_baseball.context import BaseballContext
from polars_baseball.context import cleanup as _cleanup
from polars_baseball.enums import ArsenalType, KeyType

__version__ = "0.1.1"

_logging.getLogger("polars_baseball").addHandler(_logging.NullHandler())


async def cleanup() -> None:
    """Close default HTTP resources held by the package-level context."""
    await _cleanup()


__all__ = [
    "ArsenalType",
    "BaseballContext",
    "FanGraphsRequest",
    "KeyType",
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
    "fg_data",
    "get_lookup_table",
    "hall_of_fame",
    "home_games",
    "lcs_logs",
    "managers",
    "managers_half",
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
    "park_codes",
    "parks",
    "people",
    "pitching",
    "pitching_post",
    "playerid_lookup",
    "player_search_list",
    "playerid_reverse_lookup",
    "rosters",
    "salaries",
    "savant_gamefeed_exit_velocity",
    "savant_gamefeed_exit_velocity_many",
    "savant_gamefeed_pitch_data",
    "savant_gamefeed_pitch_data_many",
    "schedules",
    "schools",
    "season_game_logs",
    "series_post",
    "statcast_arm_strength",
    "statcast_baserunning_run_value",
    "statcast_catcher_stance",
    "statcast_catcher_throwing",
    "standings",
    "statcast",
    "statcast_batter",
    "statcast_pitcher",
    "statcast_single_game",
    "teams_core",
    "teams_franchises",
    "teams_half",
    "teams_upstream",
    "top_prospects",
    "prospect_rankings",
    "wild_card_logs",
    "world_series_logs",
]

for _implementation_namespace in ("apis", "context", "enums", "exceptions", "gateways", "parsers"):
    globals().pop(_implementation_namespace, None)

del _implementation_namespace
