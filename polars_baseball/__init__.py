import logging as _logging

from polars_baseball import fangraphs, mlb, savant
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
from polars_baseball.apis.playerid import (
    chadwick_register,
    get_lookup_table,
    player_name_suggestions,
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
from polars_baseball.apis.standings import standings
from polars_baseball.apis.statcast import statcast, statcast_batter, statcast_pitcher, statcast_single_game
from polars_baseball.apis.teamid import team_ids
from polars_baseball.apis.top_prospects import prospect_rankings, top_prospects
from polars_baseball.context import BaseballContext, cleanup
from polars_baseball.enums import ArsenalType, KeyType

__version__ = "0.8.0"

_logging.getLogger("polars_baseball").addHandler(_logging.NullHandler())


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
    "fg_data",
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
    "prospect_rankings",
    "wild_card_logs",
    "world_series_logs",
]

for _implementation_namespace in ("apis", "context", "enums", "exceptions", "gateways", "parsers"):
    globals().pop(_implementation_namespace, None)

del _implementation_namespace
