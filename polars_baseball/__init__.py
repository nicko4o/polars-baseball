import logging as _logging

from polars_baseball import bref, fangraphs, lahman, mlb, retrosheet, savant
from polars_baseball._cache import configure_cache
from polars_baseball.apis.fangraphs import FanGraphsFilter, FanGraphsFilterOp, FanGraphsRequest, fg_data
from polars_baseball.apis.mlb import mlb_game_highlights
from polars_baseball.apis.playerid import (
    chadwick_register,
    get_lookup_table,
    player_name_suggestions,
    player_search_list,
    playerid_lookup,
    playerid_reverse_lookup,
)
from polars_baseball.apis.standings import standings
from polars_baseball.apis.statcast import statcast, statcast_batter, statcast_pitcher, statcast_single_game
from polars_baseball.apis.teamid import team_ids
from polars_baseball.apis.top_prospects import prospect_rankings, top_prospects
from polars_baseball.context import BaseballContext, cleanup
from polars_baseball.enums import ArsenalType, KeyType, MlbRosterType, MlbStatsGroup
from polars_baseball.enums.fangraphs import (
    FangraphsLeague,
    FangraphsMonth,
    FangraphsPositions,
    FangraphsStatColumn,
    FangraphsStatsCategory,
)
from polars_baseball.enums.position import Position

__version__ = "0.17.0"


_logging.getLogger("polars_baseball").addHandler(_logging.NullHandler())


__all__ = [
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
    "mlb_game_highlights",
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
]

for _implementation_namespace in ("apis", "context", "enums", "exceptions", "gateways", "parsers"):
    globals().pop(_implementation_namespace, None)

del _implementation_namespace
