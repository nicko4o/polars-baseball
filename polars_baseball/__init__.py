import logging as _logging

from polars_baseball._cache import configure_cache
from polars_baseball.apis.fangraphs import FanGraphsRequest, fg_data
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
from polars_baseball.apis.playerid import playerid_lookup
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
    "savant_gamefeed_exit_velocity",
    "savant_gamefeed_exit_velocity_many",
    "savant_gamefeed_pitch_data",
    "savant_gamefeed_pitch_data_many",
    "statcast_arm_strength",
    "statcast_baserunning_run_value",
    "statcast_catcher_stance",
    "statcast_catcher_throwing",
    "standings",
    "statcast",
    "statcast_batter",
    "statcast_pitcher",
    "statcast_single_game",
    "top_prospects",
    "prospect_rankings",
]

for _implementation_namespace in ("apis", "context", "enums", "exceptions", "gateways", "parsers"):
    globals().pop(_implementation_namespace, None)

del _implementation_namespace
