"""Baseball Savant leaderboard query mixin."""

from __future__ import annotations

import warnings
from typing import TYPE_CHECKING, Literal

import polars as pl

from polars_baseball._config import (
    SAVANT_ROOT,
)
from polars_baseball._leaderboard_registry import fetch_leaderboard
from polars_baseball.enums.pitch import norm_pitch_code
from polars_baseball.enums.position import pos_to_numeric
from polars_baseball.enums.savant import ArsenalType
from polars_baseball.exceptions import (
    InvalidParameterError,
    UpstreamParseError,
)

if TYPE_CHECKING:
    from polars_baseball.client import BaseballClient
    from polars_baseball.gateways.savant import SavantGateway

PATH_PERCENTILE_RANKINGS = "/leaderboard/percentile-rankings"
PATH_PITCH_ARSENALS = "/leaderboard/pitch-arsenals"
PATH_PITCH_MOVEMENT = "/leaderboard/pitch-movement"
PATH_ACTIVE_SPIN = "/leaderboard/active-spin"
PATH_SPIN_COMP = "/leaderboard/spin-direction-comparison"
SAVANT_CSV_PARAM = "true"
SAVANT_MIN_QUALIFYING = "q"
SAVANT_DEFAULT_PITCH_TEMPO_MIN = 250
SAVANT_INVALID_PLAYER_ID = 0
_ACTIVE_SPIN_TYPE_ORDER = ("release", "observed")
_OAA_AGGREGATE_CODES = frozenset({"IF", "OF", "ALL", ""})


class SavantLeaderboardMixin:
    """Methods for querying Baseball Savant leaderboards and statcast metrics."""

    _client: BaseballClient
    _gateway: SavantGateway

    async def _percentile_ranks_generic(
        self,
        player_type: Literal["batter", "pitcher"],
        year: int,
    ) -> pl.DataFrame:
        url = f"{SAVANT_ROOT}{PATH_PERCENTILE_RANKINGS}"
        params = {
            "type": player_type,
            "year": str(year),
            "position": "",
            "team": "",
            "csv": SAVANT_CSV_PARAM,
        }
        df = await self._gateway.get_leaderboard(url, params)
        if df.height > 0:
            if "player_name" in df.columns:
                df = df.filter(pl.col("player_name").is_not_null() & (pl.col("player_name").str.strip_chars() != ""))
            if "player_id" in df.columns:
                df = df.filter(pl.col("player_id") != SAVANT_INVALID_PLAYER_ID)
        return df

    async def batter_percentile_ranks(self, year: int) -> pl.DataFrame:
        """Fetch Statcast percentile rankings for batters."""
        return await self._percentile_ranks_generic("batter", year)

    async def pitcher_percentile_ranks(self, year: int) -> pl.DataFrame:
        """Fetch Statcast percentile rankings for pitchers."""
        return await self._percentile_ranks_generic("pitcher", year)

    async def exitvelo_barrels(
        self,
        year: int,
        player_type: Literal["batter", "pitcher"] = "batter",
        min_bbe: int | str = SAVANT_MIN_QUALIFYING,
    ) -> pl.DataFrame:
        """Fetch exit velocity and barrel rate leaderboard data."""
        return await fetch_leaderboard(
            "exitvelo_barrels", self._client, type=player_type, year=str(year), min=str(min_bbe)
        )

    async def pitcher_exitvelo_barrels(
        self,
        year: int,
        min_bbe: int | str = SAVANT_MIN_QUALIFYING,
    ) -> pl.DataFrame:
        """Fetch exit velocity and barrel rate leaderboard for pitchers."""
        return await self.exitvelo_barrels(year, "pitcher", min_bbe)

    async def expected_stats(
        self,
        year: int,
        player_type: Literal["batter", "pitcher"] = "batter",
        min_pa: int | str = SAVANT_MIN_QUALIFYING,
    ) -> pl.DataFrame:
        """Fetch expected stats (xBA, xSLG, xwOBA) leaderboard."""
        return await fetch_leaderboard(
            "expected_stats", self._client, type=player_type, year=str(year), min=str(min_pa)
        )

    async def pitcher_expected_stats(
        self,
        year: int,
        min_pa: int | str = SAVANT_MIN_QUALIFYING,
    ) -> pl.DataFrame:
        """Fetch expected stats leaderboard for pitchers."""
        return await self.expected_stats(year, "pitcher", min_pa)

    async def pitch_arsenal_stats(
        self,
        year: int,
        min_pitches: int = 250,
        player_type: Literal["batter", "pitcher"] = "pitcher",
    ) -> pl.DataFrame:
        """Fetch pitch arsenal statistics leaderboard."""
        return await fetch_leaderboard(
            "pitch_arsenal_stats", self._client, type=player_type, year=str(year), min=str(min_pitches)
        )

    async def pitcher_arsenal_stats(
        self,
        year: int,
        min_pitches: int = 250,
    ) -> pl.DataFrame:
        """Fetch pitch arsenal statistics for pitchers."""
        return await self.pitch_arsenal_stats(year, min_pitches, "pitcher")

    async def pitcher_pitch_arsenal(
        self,
        year: int,
        min_pitches: int = 250,
        arsenal_type: ArsenalType = ArsenalType.AVG_SPEED,
    ) -> pl.DataFrame:
        """Fetch pitcher pitch arsenal metrics."""
        if not isinstance(arsenal_type, ArsenalType):
            raise InvalidParameterError("arsenal_type must be an ArsenalType enum value.")
        url = f"{SAVANT_ROOT}{PATH_PITCH_ARSENALS}"
        params = {
            "year": str(year),
            "min": str(min_pitches),
            "type": arsenal_type.value,
            "hand": "",
            "csv": SAVANT_CSV_PARAM,
        }
        return await self._gateway.get_leaderboard(url, params)

    async def pitcher_pitch_movement(
        self,
        year: int,
        min_pitches: int | str = SAVANT_MIN_QUALIFYING,
        pitch_type: str = "FF",
    ) -> pl.DataFrame:
        """Fetch pitch movement leaderboard data."""
        pitch_code = norm_pitch_code(pitch_type)
        url = f"{SAVANT_ROOT}{PATH_PITCH_MOVEMENT}"
        params = {
            "year": str(year),
            "team": "",
            "min": str(min_pitches),
            "pitch_type": pitch_code,
            "hand": "",
            "x": "pitcher_break_x_hidden",
            "z": "pitcher_break_z_hidden",
            "csv": SAVANT_CSV_PARAM,
        }
        return await self._gateway.get_leaderboard(url, params)

    async def pitcher_active_spin(
        self,
        year: int,
        min_pitches: int = 250,
    ) -> pl.DataFrame:
        """Fetch pitcher active spin leaderboard data."""
        url = f"{SAVANT_ROOT}{PATH_ACTIVE_SPIN}"

        for idx, spin_type in enumerate(_ACTIVE_SPIN_TYPE_ORDER):
            params = {"year": f"{year}_{spin_type}", "min": str(min_pitches), "hand": "", "csv": SAVANT_CSV_PARAM}
            df = await self._gateway.get_optional_dataset(url, params)
            if df is not None:
                return df
            if idx == 0:
                warnings.warn(
                    f'Could not get active spin results for year {year} that are "spin-based". '
                    f'Trying to get the older "observed" results.',
                    stacklevel=2,
                )
        raise UpstreamParseError("Statcast did not return any active spin results for the query provided.")

    async def pitcher_spin_dir_comp(
        self,
        year: int,
        pitch_a: str = "FF",
        pitch_b: str = "CH",
        min_pitches: int = 100,
        pitcher_pov: bool = True,
    ) -> pl.DataFrame:
        """Fetch pitcher spin direction comparison data."""
        code_a = norm_pitch_code(pitch_a, to_word=True)
        code_b = norm_pitch_code(pitch_b, to_word=True)
        pov = "Pit" if pitcher_pov else "Bat"
        url = f"{SAVANT_ROOT}{PATH_SPIN_COMP}"
        params = {
            "year": str(year),
            "type": f"{code_a} / {code_b}",
            "min": str(min_pitches),
            "team": "",
            "pov": pov,
            "sort": "11",
            "sortDir": "asc",
            "csv": SAVANT_CSV_PARAM,
        }
        return await self._gateway.get_leaderboard(url, params)

    async def pitch_tempo(
        self,
        year: int,
        min_pitches: int = SAVANT_DEFAULT_PITCH_TEMPO_MIN,
    ) -> pl.DataFrame:
        """Fetch pitch tempo leaderboard data."""
        return await fetch_leaderboard("pitch_tempo", self._client, year=str(year), min=str(min_pitches))

    async def bat_tracking(
        self,
        year: int,
        player_type: Literal["batter", "pitcher"] = "batter",
        min_swings: int | str = SAVANT_MIN_QUALIFYING,
    ) -> pl.DataFrame:
        """Fetch bat tracking (swing path, attack angle) leaderboard data."""
        return await fetch_leaderboard(
            "bat_tracking",
            self._client,
            dateStart=f"{year}-01-01",
            dateEnd=f"{year}-12-31",
            minSwings=str(min_swings),
            type=player_type,
        )

    async def pitcher_bat_tracking(
        self,
        year: int,
        min_swings: int | str = SAVANT_MIN_QUALIFYING,
    ) -> pl.DataFrame:
        """Fetch bat tracking data for pitchers."""
        return await self.bat_tracking(year, "pitcher", min_swings)

    async def run_value(
        self,
        year: int,
        player_type: Literal["batter", "pitcher"] = "batter",
    ) -> pl.DataFrame:
        """Fetch run value leaderboard data."""
        group = "pitcher" if player_type == "pitcher" else "batter"
        return await fetch_leaderboard("run_value", self._client, year=str(year), group=group)

    async def pitcher_run_value(self, year: int) -> pl.DataFrame:
        """Fetch run value leaderboard for pitchers."""
        return await self.run_value(year, "pitcher")

    async def sprint_speed(self, year: int, min_opp: int = 10) -> pl.DataFrame:
        """Fetch sprint speed leaderboard data."""
        return await fetch_leaderboard("sprint_speed", self._client, year=str(year), min=str(min_opp))

    async def running_splits(self, year: int, min_opp: int = 5, raw_splits: bool = True) -> pl.DataFrame:
        """Fetch Statcast running splits data."""
        split_type = "raw" if raw_splits else "percent"
        return await fetch_leaderboard(
            "running_splits", self._client, type=split_type, year=str(year), min=str(min_opp)
        )

    async def base_stealing(self, year: int, min_attempts: int | str = "q") -> pl.DataFrame:
        """Fetch base stealing leaderboard data."""
        return await fetch_leaderboard("base_stealing", self._client, year=str(year), min=str(min_attempts))

    async def baserunning_run_value(self, year: int, min_opp: int = 5) -> pl.DataFrame:
        """Fetch baserunning run value leaderboard data."""
        return await fetch_leaderboard("baserunning_run_value", self._client, year=str(year), min=str(min_opp))

    async def outs_above_average(
        self,
        year: int,
        pos: int | str,
        min_att: int | str = SAVANT_MIN_QUALIFYING,
        view: str = "Fielder",
    ) -> pl.DataFrame:
        """Fetch Statcast Outs Above Average (OAA) leaderboard data."""
        pos_code = pos_to_numeric(pos)
        if pos_code == "2":
            raise InvalidParameterError("This particular leaderboard does not include catchers!")
        if pos_code in _OAA_AGGREGATE_CODES:
            raise InvalidParameterError(
                f"outs_above_average requires a specific position (e.g. 'LF', 'CF', 'RF', '1B', '2B', '3B', 'SS'), "
                f"not an aggregate code '{pos}'."
            )
        return await fetch_leaderboard(
            "outs_above_average",
            self._client,
            type=view,
            startYear=str(year),
            endYear=str(year),
            min=str(min_att),
            pos=pos_code,
        )

    async def outfield_directional_oaa(
        self,
        year: int,
        min_opp: int | str = SAVANT_MIN_QUALIFYING,
        min_attempts: int | str | None = None,
    ) -> pl.DataFrame:
        """Fetch directional Outs Above Average for outfielders."""
        attempts = min_attempts if min_attempts is not None else min_opp
        return await fetch_leaderboard("directional_oaa", self._client, year=str(year), min=str(attempts))

    async def outfield_catch_prob(
        self,
        year: int,
        min_opp: int | str = SAVANT_MIN_QUALIFYING,
        min_opportunities: int | str | None = None,
    ) -> pl.DataFrame:
        """Fetch outfielder catch probability leaderboard data."""
        opp = min_opportunities if min_opportunities is not None else min_opp
        return await fetch_leaderboard("catch_probability", self._client, year=str(year), min=str(opp))

    async def outfielder_jump(
        self,
        year: int,
        min_att: int | str = SAVANT_MIN_QUALIFYING,
        min_attempts: int | str | None = None,
    ) -> pl.DataFrame:
        """Fetch outfielder jump metric leaderboard data."""
        att = min_attempts if min_attempts is not None else min_att
        return await fetch_leaderboard("outfielder_jump", self._client, year=str(year), min=str(att))

    async def catcher_poptime(
        self,
        year: int,
        min_2b_att: int = 5,
        min_3b_att: int = 0,
        min_attempts_2b: int | None = None,
        min_attempts_3b: int | None = None,
    ) -> pl.DataFrame:
        """Fetch catcher pop time leaderboard data."""
        att_2b = min_attempts_2b if min_attempts_2b is not None else min_2b_att
        att_3b = min_attempts_3b if min_attempts_3b is not None else min_3b_att
        return await fetch_leaderboard("poptime", self._client, year=str(year), min2b=str(att_2b), min3b=str(att_3b))

    async def catcher_framing(
        self,
        year: int,
        min_called_p: int | str = SAVANT_MIN_QUALIFYING,
        min_called_pitches: int | str | None = None,
    ) -> pl.DataFrame:
        """Fetch catcher framing leaderboard data."""
        called_p = min_called_pitches if min_called_pitches is not None else min_called_p
        df = await fetch_leaderboard(
            "catcher_framing", self._client, seasonStart=str(year), seasonEnd=str(year), min=str(called_p)
        )
        if df.height > 0 and "name" in df.columns:
            df = df.filter(pl.col("name").is_not_null() & (pl.col("name").str.strip_chars() != ""))
        return df

    async def catcher_blocking(self, year: int, min_chances: int = 100) -> pl.DataFrame:
        """Fetch catcher blocking leaderboard data."""
        return await fetch_leaderboard("catcher_blocking", self._client, year=str(year), min_chances=str(min_chances))

    async def arm_strength(self, year: int, min_throws: int = 50) -> pl.DataFrame:
        """Fetch arm strength leaderboard data."""
        return await fetch_leaderboard("arm_strength", self._client, year=str(year), min=str(min_throws))

    async def catcher_throwing(
        self,
        year: int,
        min_att: int = 5,
        min_attempts: int | None = None,
    ) -> pl.DataFrame:
        """Fetch catcher throwing run value leaderboard data."""
        att = min_attempts if min_attempts is not None else min_att
        return await fetch_leaderboard("catcher_throwing", self._client, year=str(year), min_att=str(att))

    async def catcher_stance(self, year: int) -> pl.DataFrame:
        """Fetch catcher stance data."""
        return await fetch_leaderboard("catcher_stance", self._client, year=str(year))

    async def fielding_run_value(
        self,
        year: int,
        position: int | str | None = None,
        pos: int | str | None = None,
        min_inn: int | None = None,
    ) -> pl.DataFrame:
        """Fetch fielding run value leaderboard data."""
        target_pos = position if position is not None else pos
        pos_str = "" if target_pos is None else pos_to_numeric(target_pos)
        min_str = "" if min_inn is None else str(min_inn)
        return await fetch_leaderboard(
            "fielding_run_value",
            self._client,
            seasonStart=str(year),
            seasonEnd=str(year),
            position=pos_str,
            minInnings=min_str,
        )
