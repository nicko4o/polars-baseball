from datetime import timedelta
from typing import Final

import polars as pl

from polars_baseball._cache import cached, generate_cache_key
from polars_baseball._config import MILB_ROOT, MLB_ROOT
from polars_baseball.apis.mlb.team_lookup import resolve_team_id
from polars_baseball.context import BaseballContext, default_context
from polars_baseball.exceptions import InvalidParameterError, UpstreamParseError
from polars_baseball.parsers.mlb import MLBApiParser
from polars_baseball.parsers.pipeline import MLBPipelineParser

_HTML_ENCODING = "utf-8"
_BATTERS_PLAYER_TYPE = "batters"
_PITCHERS_PLAYER_TYPE = "pitchers"
_VALID_PLAYER_TYPES: Final[frozenset[str]] = frozenset({_BATTERS_PLAYER_TYPE, _PITCHERS_PLAYER_TYPE})


def _postprocess(df: pl.DataFrame) -> pl.DataFrame:
    cols_to_drop = [col for col in df.columns if "Tm" in col or "Unnamed" in col]
    return df.drop(cols_to_drop) if cols_to_drop else df


def _align_schemas(dfs: list[pl.DataFrame]) -> list[pl.DataFrame]:
    if not dfs or len(dfs) == 1:
        return dfs

    col_types: dict[str, set[pl.DataType]] = {}
    for df in dfs:
        for col, dtype in df.schema.items():
            col_types.setdefault(col, set()).add(dtype)

    cast_rules: dict[str, pl.DataType] = {}
    for col, dtypes in col_types.items():
        if len(dtypes) > 1:
            if any(dt == pl.String or isinstance(dt, pl.String) for dt in dtypes):
                cast_rules[col] = pl.String()
            elif any(dt == pl.Float64 or isinstance(dt, pl.Float64) for dt in dtypes):
                cast_rules[col] = pl.Float64()
            else:
                cast_rules[col] = pl.String()

    if not cast_rules:
        return dfs

    return [
        df.with_columns(
            [pl.col(col).cast(target_dtype) for col, target_dtype in cast_rules.items() if col in df.columns]
        )
        for df in dfs
    ]


def _top_prospects_cache_key(team_name: str | None = None, player_type: str | None = None, **kwargs: object) -> str:
    clean_team = "league" if team_name is None else team_name.lower().strip()
    clean_type = "all" if player_type is None else player_type.lower().strip()
    return generate_cache_key("mlb/top_prospects", {"team": clean_team, "type": clean_type})


async def _resolve_prospects_url(team_name: str | None, context: BaseballContext | None = None) -> str:
    if team_name is None:
        return f"{MLB_ROOT}/prospects/stats/top-prospects"

    team_id = await resolve_team_id(team_name, context=context)
    return f"{MLB_ROOT}/prospects/stats?teamId={team_id}"


def _select_prospect_table(dfs: list[pl.DataFrame], player_type: str | None) -> pl.DataFrame:
    if player_type == _BATTERS_PLAYER_TYPE:
        return dfs[0]

    if player_type == _PITCHERS_PLAYER_TYPE:
        if len(dfs) < 2:
            raise UpstreamParseError("MLB top prospects response did not contain a pitchers table.")
        return dfs[1]

    return pl.concat(_align_schemas(dfs), how="diagonal")


@cached(key=_top_prospects_cache_key, max_age=timedelta(days=1))
async def top_prospects(
    team_name: str | None = None,
    player_type: str | None = None,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch MLB top prospects for a team or the full league.

    Supports filtering by player_type (batters/pitchers). When team_name
    is None, returns league-wide top prospects from the main prospect hub.
    """
    if player_type is not None and player_type not in _VALID_PLAYER_TYPES:
        raise InvalidParameterError("player_type must be one of: batters, pitchers.")

    ctx = context or default_context()
    url = await _resolve_prospects_url(team_name, context=ctx)
    html_str = await ctx.http.get_text(url)
    if not html_str:
        raise UpstreamParseError("MLB top prospects returned empty response.")

    parser = MLBApiParser()
    dfs = parser.parse_tables(html_str)
    if not dfs:
        raise UpstreamParseError("MLB top prospects response did not contain prospect tables.")

    df = _select_prospect_table(dfs, player_type)

    if "Rk" in df.columns:
        df = df.sort("Rk")
    return _postprocess(df)


def _prospect_rankings_cache_key(list_type: str = "top100", year: int | None = None, **kwargs: object) -> str:
    str_year = "current" if year is None else str(year)
    return generate_cache_key("milb/prospect_rankings", {"list_type": list_type.lower().strip(), "year": str_year})


def _prospect_rankings_max_age(year: int | None = None, **kwargs: object) -> timedelta | None:
    if year is None:
        return timedelta(days=1)
    from polars_baseball._season import most_recent_season

    return timedelta(days=1) if year >= most_recent_season() else None


@cached(key=_prospect_rankings_cache_key, max_age=_prospect_rankings_max_age)
async def prospect_rankings(
    list_type: str = "top100",
    year: int | None = None,
    context: BaseballContext | None = None,
) -> pl.DataFrame:
    """Fetch MLB Pipeline prospect rankings.

    Supports top100, draft, international, positional rankings (1b, 2b, 3b, ss, c, of, rhp, lhp),
    and team-specific top 30 rankings (e.g. yankees, redsox, dbacks).
    Also supports historical rankings by specifying the year.
    """
    list_type_clean = list_type.lower().strip()

    if year is not None:
        from polars_baseball._config import PROSPECT_RANKINGS_START_YEAR
        from polars_baseball._season import most_recent_season

        max_year = most_recent_season() + 4
        if year < PROSPECT_RANKINGS_START_YEAR or year > max_year:
            raise InvalidParameterError(f"Year must be between {PROSPECT_RANKINGS_START_YEAR} and {max_year}.")

    if year is not None:
        base_path = f"{MILB_ROOT}/prospects/{year}"
    else:
        base_path = f"{MILB_ROOT}/prospects"

    url = base_path if list_type_clean == "top100" else f"{base_path}/{list_type_clean}"

    ctx = context or default_context()
    html_str = await ctx.http.get_text(url)
    if not html_str:
        raise UpstreamParseError(f"MLB pipeline prospects returned empty response for: {url}")

    parser = MLBPipelineParser()
    return parser.parse(html_str)
