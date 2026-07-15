"""Convenience namespace for MLB Stats API endpoints."""

from polars_baseball.apis.mlb import (
    mlb_divisions as divisions,
)
from polars_baseball.apis.mlb import (
    mlb_draft as draft,
)
from polars_baseball.apis.mlb import (
    mlb_game_boxscore as game_boxscore,
)
from polars_baseball.apis.mlb import (
    mlb_game_boxscore_stats as game_boxscore_stats,
)
from polars_baseball.apis.mlb import (
    mlb_game_feed_live as game_feed_live,
)
from polars_baseball.apis.mlb import (
    mlb_game_linescore as game_linescore,
)
from polars_baseball.apis.mlb import (
    mlb_game_play_by_play as game_play_by_play,
)
from polars_baseball.apis.mlb import (
    mlb_game_win_probability as game_win_probability,
)
from polars_baseball.apis.mlb import (
    mlb_leagues as leagues,
)
from polars_baseball.apis.mlb import (
    mlb_people as people,
)
from polars_baseball.apis.mlb import (
    mlb_people_awards as people_awards,
)
from polars_baseball.apis.mlb import (
    mlb_pitch_arsenal as pitch_arsenal,
)
from polars_baseball.apis.mlb import (
    mlb_player_stats as player_stats,
)
from polars_baseball.apis.mlb import (
    mlb_postseason_schedule as postseason_schedule,
)
from polars_baseball.apis.mlb import (
    mlb_roster as roster,
)
from polars_baseball.apis.mlb import (
    mlb_schedule as schedule,
)
from polars_baseball.apis.mlb import (
    mlb_stat_leaders as stat_leaders,
)
from polars_baseball.apis.mlb import (
    mlb_team_stats as team_stats,
)
from polars_baseball.apis.mlb import (
    mlb_teams as teams,
)
from polars_baseball.apis.mlb import (
    mlb_transactions as transactions,
)
from polars_baseball.apis.mlb import (
    mlb_venues as venues,
)

__all__ = [
    "divisions",
    "draft",
    "game_boxscore",
    "game_boxscore_stats",
    "game_feed_live",
    "game_linescore",
    "game_play_by_play",
    "game_win_probability",
    "leagues",
    "people",
    "people_awards",
    "pitch_arsenal",
    "player_stats",
    "postseason_schedule",
    "roster",
    "schedule",
    "stat_leaders",
    "team_stats",
    "teams",
    "transactions",
    "venues",
]
