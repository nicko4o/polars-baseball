from dataclasses import dataclass

import polars as pl

from polars_baseball._config import SAVANT_ROOT
from polars_baseball.context import BaseballContext
from polars_baseball.gateways.savant import SavantGateway


@dataclass(frozen=True)
class LeaderboardDef:
    path: str
    params: dict[str, str | None]  # None = fill from kwargs by key name

    def build_params(self, **kwargs: object) -> dict[str, str]:
        result: dict[str, str] = {}
        for k, v in self.params.items():
            if v is None:
                val = kwargs.get(k)
                if val is None:
                    result[k] = ""
                else:
                    result[k] = str(val)
            else:
                result[k] = v
        result["csv"] = "true"
        return result


LEADERBOARDS: dict[str, LeaderboardDef] = {
    "exitvelo_barrels": LeaderboardDef(
        path="/leaderboard/statcast",
        params={"type": None, "year": None, "position": "", "team": "", "min": None},
    ),
    "expected_stats": LeaderboardDef(
        path="/leaderboard/expected_statistics",
        params={"type": None, "year": None, "position": "", "team": "", "filterType": "pa", "min": None},
    ),
    "pitch_arsenal_stats": LeaderboardDef(
        path="/leaderboard/pitch-arsenal-stats",
        params={"type": None, "pitchType": "", "year": None, "team": "", "min": None},
    ),
    "bat_tracking": LeaderboardDef(
        path="/leaderboard/bat-tracking/swing-path-attack-angle",
        params={
            "dateStart": None,
            "dateEnd": None,
            "gameType": "Regular",
            "minSwings": None,
            "minGroupSwings": "1",
            "seasonStart": None,
            "seasonEnd": None,
            "type": None,
        },
    ),
    "run_value": LeaderboardDef(
        path="/leaderboard/swing-take",
        params={
            "year": None,
            "team": "",
            "leverage": "Neutral",
            "group": None,
            "type": "All",
            "sub_type": "null",
            "min": "q",
        },
    ),
    "sprint_speed": LeaderboardDef(
        path="/leaderboard/sprint_speed",
        params={"year": None, "position": "", "team": "", "min": None},
    ),
    "running_splits": LeaderboardDef(
        path="/running_splits",
        params={"type": None, "bats": "", "year": None, "position": "", "team": "", "min": None},
    ),
    "base_stealing": LeaderboardDef(
        path="/leaderboard/basestealing-run-value",
        params={"year": None, "min": None},
    ),
    "fielding_run_value": LeaderboardDef(
        path="/leaderboard/fielding-run-value",
        params={
            "gameType": "Regular",
            "seasonStart": None,
            "seasonEnd": None,
            "type": "fielder",
            "position": None,
            "minInnings": None,
            "minResults": "1",
        },
    ),
    "directional_oaa": LeaderboardDef(
        path="/directional_outs_above_average",
        params={"year": None, "min": None, "team": ""},
    ),
    "catch_probability": LeaderboardDef(
        path="/leaderboard/catch_probability",
        params={"type": "player", "min": None, "year": None, "total": ""},
    ),
    "outfielder_jump": LeaderboardDef(
        path="/leaderboard/outfield_jump",
        params={"year": None, "min": None},
    ),
    "poptime": LeaderboardDef(
        path="/leaderboard/poptime",
        params={"year": None, "team": "", "min2b": None, "min3b": None},
    ),
    "catcher_framing": LeaderboardDef(
        path="/leaderboard/catcher-framing",
        params={
            "type": "catcher",
            "seasonStart": None,
            "seasonEnd": None,
            "team": "",
            "min": None,
            "sortColumn": "rv_tot",
            "sortDirection": "desc",
        },
    ),
    "catcher_blocking": LeaderboardDef(
        path="/leaderboard/catcher-blocking",
        params={"year": None, "min_chances": None},
    ),
    "pitch_tempo": LeaderboardDef(
        path="/leaderboard/pitch-tempo",
        params={"year": None, "min": None},
    ),
    "arm_strength": LeaderboardDef(
        path="/leaderboard/arm-strength",
        params={"type": "player", "year": None, "position": "", "team": "", "min": None},
    ),
    "baserunning_run_value": LeaderboardDef(
        path="/leaderboard/baserunning-run-value",
        params={"year": None, "min": None},
    ),
    "catcher_throwing": LeaderboardDef(
        path="/leaderboard/catcher-throwing",
        params={"year": None, "min_att": None},
    ),
    "catcher_stance": LeaderboardDef(
        path="/leaderboard/catcher-stance",
        params={"year": None},
    ),
    # The following Savant leaderboard paths could not be confirmed via live probe
    # and are shelved pending upstream availability:
    # swing_timing            → /leaderboard/swing-timing-miss-distance (404)
    # arm_value               → /leaderboard/arm-value (404)
    # extra_bases_taken       → /leaderboard/extra-bases-taken-run-value (404)
    "outs_above_average": LeaderboardDef(
        path="/leaderboard/outs_above_average",
        params={
            "type": None,
            "startYear": None,
            "endYear": None,
            "split": "no",
            "team": "",
            "range": "year",
            "min": None,
            "pos": None,
            "roles": "",
            "viz": "hide",
        },
    ),
}


async def get_leaderboard(
    name: str,
    context: BaseballContext | None = None,
    **kwargs: object,
) -> pl.DataFrame:
    ctx = context or BaseballContext.default()
    reg = LEADERBOARDS.get(name)
    if reg is None:
        msg = f"Unknown leaderboard: {name}"
        raise ValueError(msg)
    url = f"{SAVANT_ROOT}{reg.path}"
    params = reg.build_params(**kwargs)
    return await SavantGateway(ctx).get_leaderboard(url, params)
