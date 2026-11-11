"""MLB Stats API parsers for game data—boxscores, boxscore stats, play-by-play, win probability, and linescore."""

import re
from typing import Final, cast

import polars as pl

from polars_baseball._json_utils import JsonObject, safe_child_dict, to_int
from polars_baseball._schema_utils import validate_and_cast_schema
from polars_baseball._schemas.mlb import (
    MLB_BOXSCORE_REQUIRED,
    MLB_BOXSCORE_STATS_TYPES,
    MLB_BOXSCORE_TYPES,
    MLB_GAME_HIGHLIGHTS_REQUIRED,
    MLB_GAME_HIGHLIGHTS_TYPES,
    MLB_LINESCORE_REQUIRED,
    MLB_LINESCORE_TYPES,
    MLB_LIVE_FEED_REQUIRED,
    MLB_LIVE_FEED_TYPES,
    MLB_PBP_REQUIRED,
    MLB_PBP_TYPES,
)
from polars_baseball.parsers.mlb.types import BoxscorePlayerDict, LinescoreDict, LiveFeedPitchDict, PlayByPlayDict


def _parse_batting_order(player_data: JsonObject) -> int | None:
    return to_int(player_data.get("battingOrder"))


def parse_boxscore_player(
    player_data: JsonObject,
    game_pk: int,
    team_id: int | None,
) -> BoxscorePlayerDict:
    person = safe_child_dict(player_data, "person")
    pos = safe_child_dict(player_data, "position")
    stats = safe_child_dict(player_data, "stats")
    batting_order = _parse_batting_order(player_data)
    row: dict[str, object] = {
        "gamePk": game_pk,
        "teamId": team_id,
        "personId": to_int(person.get("id")),
        "fullName": person.get("fullName"),
        "jerseyNumber": player_data.get("jerseyNumber"),
        "positionCode": pos.get("code"),
        "positionName": pos.get("name"),
        "positionAbbrev": pos.get("abbreviation"),
        "isInBattingOrder": batting_order is not None,
        "battingOrder": batting_order,
    }
    for group in ("batting", "pitching", "fielding"):
        group_stats = safe_child_dict(stats, group)
        for key, value in group_stats.items():
            if isinstance(value, dict):
                continue
            row[f"{group}_{key}"] = value
    return cast(BoxscorePlayerDict, row)


def parse_boxscore(data: JsonObject, game_pk: int) -> list[BoxscorePlayerDict]:
    rows: list[BoxscorePlayerDict] = []
    teams = safe_child_dict(data, "teams")
    for team_type in ("away", "home"):
        team_data = safe_child_dict(teams, team_type)
        team_sub = safe_child_dict(team_data, "team")
        team_id = to_int(team_sub.get("id"))
        players = safe_child_dict(team_data, "players")
        for player_data in players.values():
            if isinstance(player_data, dict):
                rows.append(parse_boxscore_player(cast(JsonObject, player_data), game_pk, team_id))
    return rows


def parse_play(play: JsonObject, game_pk: int) -> PlayByPlayDict:
    about = safe_child_dict(play, "about")
    result = safe_child_dict(play, "result")
    matchup = safe_child_dict(play, "matchup")
    count = safe_child_dict(play, "count")
    batter = safe_child_dict(matchup, "batter")
    pitcher = safe_child_dict(matchup, "pitcher")
    return cast(
        PlayByPlayDict,
        {
            "gamePk": game_pk,
            "atBatIndex": about.get("atBatIndex"),
            "inning": about.get("inning"),
            "halfInning": about.get("halfInning"),
            "batterId": batter.get("id"),
            "batterName": batter.get("fullName"),
            "pitcherId": pitcher.get("id"),
            "pitcherName": pitcher.get("fullName"),
            "description": result.get("description"),
            "event": result.get("event"),
            "eventType": result.get("eventType"),
            "balls": count.get("balls"),
            "strikes": count.get("strikes"),
            "outs": count.get("outs"),
            "homeScore": result.get("homeScore"),
            "awayScore": result.get("awayScore"),
            "rbi": result.get("rbi"),
            "homeTeamWinProbability": play.get("homeTeamWinProbability"),
            "awayTeamWinProbability": play.get("awayTeamWinProbability"),
            "homeTeamWinProbabilityAdded": play.get("homeTeamWinProbabilityAdded"),
            "leverageIndex": play.get("leverageIndex"),
            "dramaIndex": play.get("dramaIndex"),
        },
    )


def parse_live_feed_pitch(
    event_data: JsonObject,
    play_data: JsonObject,
    game_pk: int,
) -> LiveFeedPitchDict:
    about = safe_child_dict(play_data, "about")
    matchup = safe_child_dict(play_data, "matchup")
    batter = safe_child_dict(matchup, "batter")
    pitcher = safe_child_dict(matchup, "pitcher")
    details = safe_child_dict(event_data, "details")
    pitch_type = safe_child_dict(details, "type")
    pitch_data = safe_child_dict(event_data, "pitchData")
    breaks = safe_child_dict(pitch_data, "breaks")

    raw_play_id = event_data.get("playId") or event_data.get("guid") or about.get("playId")
    play_id = str(raw_play_id).strip() if raw_play_id else None

    return cast(
        LiveFeedPitchDict,
        {
            "gamePk": game_pk,
            "atBatIndex": about.get("atBatIndex"),
            "pitchIndex": event_data.get("index"),
            "pitchNumber": event_data.get("pitchNumber"),
            "playId": play_id,
            "batterId": batter.get("id"),
            "batterName": batter.get("fullName"),
            "pitcherId": pitcher.get("id"),
            "pitcherName": pitcher.get("fullName"),
            "event": details.get("event"),
            "description": details.get("description"),
            "pitchType": pitch_type.get("code"),
            "releaseSpeed": pitch_data.get("startSpeed"),
            "spinRate": breaks.get("spinRate"),
        },
    )


def parse_linescore(data: JsonObject, game_pk: int) -> list[LinescoreDict]:
    innings = data.get("innings", [])
    if not isinstance(innings, list):
        return []
    rows: list[LinescoreDict] = []
    for inn in innings:
        if not isinstance(inn, dict):
            continue
        home_data = safe_child_dict(inn, "home")
        away_data = safe_child_dict(inn, "away")
        rows.append(
            cast(
                LinescoreDict,
                {
                    "gamePk": game_pk,
                    "inning": inn.get("num"),
                    "homeRuns": home_data.get("runs"),
                    "homeHits": home_data.get("hits"),
                    "homeErrors": home_data.get("errors"),
                    "awayRuns": away_data.get("runs"),
                    "awayHits": away_data.get("hits"),
                    "awayErrors": away_data.get("errors"),
                },
            )
        )
    return rows


def parse_mlb_boxscore(data: JsonObject, game_pk: int) -> pl.DataFrame:
    """Parse boxscore from MLB Stats API /game/{gamePk}/boxscore response.

    Iterates both away and home teams, extracting each player's basic
    info, position, batting order, and stat groups (batting, pitching,
    fielding) flattened into prefixed columns.
    """
    rows = parse_boxscore(data, game_pk)
    if not rows:
        return pl.DataFrame(schema=MLB_BOXSCORE_TYPES)
    return validate_and_cast_schema(
        pl.DataFrame(rows, infer_schema_length=None), MLB_BOXSCORE_REQUIRED, MLB_BOXSCORE_TYPES
    )


def parse_mlb_boxscore_stats(data: JsonObject, game_pk: int) -> pl.DataFrame:
    """Parse boxscore stats from MLB Stats API /game/{gamePk}/boxscore response.

    Identical structure to parse_mlb_boxscore but validates against the
    boxscore stats type schema which includes stat columns from the
    batting, pitching, and fielding groups.
    """
    rows = parse_boxscore(data, game_pk)
    if not rows:
        return pl.DataFrame(schema=MLB_BOXSCORE_STATS_TYPES)
    return validate_and_cast_schema(
        pl.DataFrame(rows, infer_schema_length=None), MLB_BOXSCORE_REQUIRED, MLB_BOXSCORE_STATS_TYPES
    )


def parse_mlb_play_by_play(data: JsonObject, game_pk: int) -> pl.DataFrame:
    """Parse play-by-play from MLB Stats API /game/{gamePk}/feed/live response.

    Extracts each play in liveData.plays.allPlays[], flattening the
    about, result, matchup, and count sub-objects. Includes win
    probability and leverage index fields.
    """
    plays = data.get("allPlays", [])
    if not isinstance(plays, list) or not plays:
        return pl.DataFrame(schema=MLB_PBP_TYPES)
    rows = [parse_play(cast(JsonObject, play), game_pk) for play in plays if isinstance(play, dict)]
    return validate_and_cast_schema(pl.DataFrame(rows, schema=MLB_PBP_TYPES), MLB_PBP_REQUIRED, MLB_PBP_TYPES)


def parse_mlb_win_probability(data: object, game_pk: int) -> pl.DataFrame:
    """Parse win probability data from MLB Stats API win probability endpoint.

    Accepts a raw list of play objects rather than a wrapper dict.
    Each play is parsed identically to parse_mlb_play_by_play.

    Note:
        Non-dict entries in the list are silently skipped. Returns an
        empty DataFrame when data is not a list.
    """
    if not isinstance(data, list):
        return pl.DataFrame(schema=MLB_PBP_TYPES)
    rows = [parse_play(cast(JsonObject, play), game_pk) for play in data if isinstance(play, dict)]
    if not rows:
        return pl.DataFrame(schema=MLB_PBP_TYPES)
    return validate_and_cast_schema(pl.DataFrame(rows, schema=MLB_PBP_TYPES), MLB_PBP_REQUIRED, MLB_PBP_TYPES)


def parse_mlb_game_feed_live(data: JsonObject, game_pk: int) -> pl.DataFrame:
    """Parse live game feed from MLB Stats API /game/{gamePk}/feed/live (v1.1).

    Extracts pitch-level events from liveData.plays.allPlays[].playEvents[].
    Only events flagged as isPitch are included.

    Note:
        Returns empty DataFrame when no pitch events are found or when
        liveData/plays/allPlays keys are missing.
    """
    live_data = safe_child_dict(data, "liveData")
    plays = safe_child_dict(live_data, "plays")
    all_plays = plays.get("allPlays", [])
    if not isinstance(all_plays, list):
        return pl.DataFrame(schema=MLB_LIVE_FEED_TYPES)
    rows: list[LiveFeedPitchDict] = []
    for play in all_plays:
        if not isinstance(play, dict):
            continue
        play_events = play.get("playEvents", [])
        if not isinstance(play_events, list):
            continue
        for event in play_events:
            if isinstance(event, dict) and event.get("isPitch"):
                rows.append(parse_live_feed_pitch(cast(JsonObject, event), cast(JsonObject, play), game_pk))
    if not rows:
        return pl.DataFrame(schema=MLB_LIVE_FEED_TYPES)
    return validate_and_cast_schema(
        pl.DataFrame(rows, schema=MLB_LIVE_FEED_TYPES), MLB_LIVE_FEED_REQUIRED, MLB_LIVE_FEED_TYPES
    )


def parse_mlb_game_linescore(data: JsonObject, game_pk: int) -> pl.DataFrame:
    """Parse linescore from MLB Stats API /game/{gamePk}/linescore response.

    Extracts each inning from the innings[] array, capturing runs,
    hits, and errors for both home and away teams.

    Note:
        Innings with non-dict values are silently skipped.
    """
    rows = parse_linescore(data, game_pk)
    if not rows:
        return pl.DataFrame(schema=MLB_LINESCORE_TYPES)
    return validate_and_cast_schema(
        pl.DataFrame(rows, schema=MLB_LINESCORE_TYPES), MLB_LINESCORE_REQUIRED, MLB_LINESCORE_TYPES
    )


_BITRATE_REGEX: Final[re.Pattern[str]] = re.compile(r"(\d+)[kK]")


def _extract_playback_bitrate(url: str) -> int:
    match = _BITRATE_REGEX.search(url)
    return int(match.group(1)) if match else 0


def _select_highest_bitrate_playback_url(playbacks: list[JsonObject]) -> str | None:
    if not playbacks:
        return None

    valid_urls: list[str] = [
        cast(str, pb["url"]) for pb in playbacks if isinstance(pb, dict) and isinstance(pb.get("url"), str)
    ]
    if not valid_urls:
        return None

    return max(valid_urls, key=_extract_playback_bitrate)


def _extract_keyword_value(keywords_all: object, target_type: str) -> str | None:
    if not isinstance(keywords_all, list):
        return None
    for kw in keywords_all:
        if isinstance(kw, dict) and kw.get("type") == target_type and kw.get("value") is not None:
            return str(kw.get("value"))
    return None


def _parse_highlight_item(item: JsonObject, game_pk: int) -> dict[str, object] | None:
    playbacks = item.get("playbacks", [])
    best_url = _select_highest_bitrate_playback_url(
        [cast(JsonObject, pb) for pb in playbacks if isinstance(pb, dict)] if isinstance(playbacks, list) else []
    )
    if not best_url:
        return None

    keywords_all = item.get("keywordsAll", [])
    raw_player_id = _extract_keyword_value(keywords_all, "player_id")
    try:
        player_id = int(raw_player_id) if raw_player_id is not None else None
    except ValueError:
        player_id = None

    raw_play_id = item.get("guid") or item.get("playId") or _extract_keyword_value(keywords_all, "play_id")
    play_id = str(raw_play_id).strip() if raw_play_id else None
    raw_id = item.get("id") or item.get("mediaPlaybackId")
    highlight_id = str(raw_id) if raw_id is not None else None

    return {
        "gamePk": game_pk,
        "highlightId": highlight_id,
        "playId": play_id,
        "playerId": player_id,
        "title": item.get("headline"),
        "blurb": item.get("blurb"),
        "description": item.get("description"),
        "duration": item.get("duration"),
        "date": item.get("date"),
        "url": best_url,
        "best_mp4_url": best_url,
    }


def parse_mlb_game_highlights(data: JsonObject, game_pk: int) -> pl.DataFrame:
    """Parse highlight metadata and playback URLs from MLB Stats API /game/{gamePk}/content response."""
    highlights_container = safe_child_dict(data, "highlights")
    inner_highlights = safe_child_dict(highlights_container, "highlights")
    items = inner_highlights.get("items", [])
    if not isinstance(items, list) or not items:
        return pl.DataFrame(schema=MLB_GAME_HIGHLIGHTS_TYPES)

    rows: list[dict[str, object]] = []
    for item in items:
        if isinstance(item, dict):
            row = _parse_highlight_item(cast(JsonObject, item), game_pk)
            if row is not None:
                rows.append(row)

    if not rows:
        return pl.DataFrame(schema=MLB_GAME_HIGHLIGHTS_TYPES)

    return validate_and_cast_schema(
        pl.DataFrame(rows, schema=MLB_GAME_HIGHLIGHTS_TYPES),
        MLB_GAME_HIGHLIGHTS_REQUIRED,
        MLB_GAME_HIGHLIGHTS_TYPES,
    )
