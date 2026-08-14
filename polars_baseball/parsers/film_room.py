import re
from collections.abc import Mapping
from datetime import date, datetime
from typing import Any

import polars as pl

from polars_baseball.exceptions import UpstreamParseError

PLAYBACK_SCHEMA = pl.Struct(
    {
        "name": pl.Utf8,
        "url": pl.Utf8,
        "bitrate": pl.Int64,
        "width": pl.Int64,
        "height": pl.Int64,
    }
)

FILM_ROOM_SCHEMA: Mapping[str, pl.DataType | type[pl.DataType]] = {
    "content_id": pl.Utf8,
    "date": pl.Date,
    "title": pl.Utf8,
    "blurb": pl.Utf8,
    "player_id": pl.Int64,
    "player_name": pl.Utf8,
    "event_type": pl.Utf8,
    "exit_velocity": pl.Float64,
    "hit_distance": pl.Int64,
    "best_mp4_url": pl.Utf8,
    "hls_url": pl.Utf8,
    "playbacks": pl.List(PLAYBACK_SCHEMA),
}


_FOUR_K_SHORT_LABEL_VALUE = 4
_FOUR_K_CANONICAL_BITRATE = 4000
_MBPS_TO_KBPS_MULTIPLIER = 1000


def _extract_bitrate(name: str, url: str) -> int:
    match = re.search(r"(\d+)K", name, re.IGNORECASE) or re.search(r"(\d+)K", url, re.IGNORECASE)
    if match:
        val = int(match.group(1))
        return _FOUR_K_CANONICAL_BITRATE if val == _FOUR_K_SHORT_LABEL_VALUE else val
    match_mb = re.search(r"(\d+)M", name, re.IGNORECASE)
    if match_mb:
        return int(match_mb.group(1)) * _MBPS_TO_KBPS_MULTIPLIER
    return 0


def _parse_date(val: Any) -> date | None:
    if not isinstance(val, str) or not val:
        return None
    cleaned = val.split("T")[0]
    try:
        return datetime.strptime(cleaned, "%Y-%m-%d").date()
    except ValueError:
        return None


def _clean_event_type(raw_val: str) -> str:
    cleaned = raw_val.strip("[]")
    parts = [p.strip() for p in cleaned.split(",") if p.strip()]
    if not parts:
        return raw_val
    for p in reversed(parts):
        if p.lower() not in ("hit", "out", "play"):
            return p
    return parts[-1]


def _extract_raw_items(data: dict[str, Any]) -> list[Any]:
    if "data" in data and isinstance(data["data"], dict):
        gdata = data["data"]
        if "search" in gdata and isinstance(gdata["search"], dict):
            plays = gdata["search"].get("plays", [])
            return list(plays) if isinstance(plays, list) else []
        if "mediaPlayback" in gdata and isinstance(gdata["mediaPlayback"], list):
            return list(gdata["mediaPlayback"])
    for key in ("plays", "highlights", "items"):
        if key in data and isinstance(data[key], list):
            return list(data[key])
    return []


def _parse_fields(fields: list[Any]) -> dict[str, Any]:
    res: dict[str, Any] = {}
    for f in fields:
        if not isinstance(f, dict):
            continue
        fname = str(f.get("name") or "").lower()
        fval = str(f.get("value") or "")
        fdisp = str(f.get("displayValue") or "")
        if fname in ("playerid", "player_id"):
            raw_id = fval.split(",")[0].strip()
            try:
                res["player_id"] = int(raw_id)
            except ValueError:
                pass
            if fdisp and "player_name" not in res:
                res["player_name"] = fdisp.split(",")[0].strip()
        elif fname in ("playername", "player_name"):
            res["player_name"] = fdisp or fval
        elif fname in ("eventtype", "event_type", "hitresult", "event"):
            res["event_type"] = _clean_event_type(fdisp or fval)
        elif fname in ("exitvelocity", "exit_velocity", "launch_speed"):
            try:
                res["exit_velocity"] = float(fval)
            except ValueError:
                pass
        elif fname in ("hitdistance", "hit_distance", "launch_angle_distance"):
            try:
                res["hit_distance"] = int(float(fval))
            except ValueError:
                pass
    return res


def _parse_playbacks(raw_playbacks: Any) -> tuple[list[dict[str, Any]], str | None, str | None]:
    if isinstance(raw_playbacks, dict) and "playbacks" in raw_playbacks:
        raw_playbacks = raw_playbacks["playbacks"]
    if not isinstance(raw_playbacks, list):
        return [], None, None

    playback_list: list[dict[str, Any]] = []
    best_mp4_url: str | None = None
    best_bitrate = -1
    hls_url: str | None = None

    for p in raw_playbacks:
        if not isinstance(p, dict):
            continue
        pname = str(p.get("name") or p.get("type") or "")
        purl = str(p.get("url") or p.get("href") or "")
        if not purl:
            continue

        bitrate = int(p.get("bitrate") or _extract_bitrate(pname, purl))
        playback_list.append(
            {
                "name": pname,
                "url": purl,
                "bitrate": bitrate,
                "width": int(p.get("width") or 0),
                "height": int(p.get("height") or 0),
            }
        )
        if purl.endswith(".m3u8") and not hls_url:
            hls_url = purl
        elif (purl.endswith(".mp4") or "mp4" in pname.lower()) and bitrate > best_bitrate:
            best_bitrate = bitrate
            best_mp4_url = purl

    return playback_list, best_mp4_url, hls_url


_FORGE_DEFAULT_BITRATE = _FOUR_K_CANONICAL_BITRATE
_FORGE_DEFAULT_WIDTH = 1280
_FORGE_DEFAULT_HEIGHT = 720
_FORGE_DEFAULT_FPS = 59
_FORGE_CDN_BASE_URL = "https://mlb-cuts-diamond.mlb.com/FORGE"


def _build_forge_cdn_mp4_url(media_playback_id: str, dt: date | None) -> str | None:
    if not media_playback_id or dt is None:
        return None
    year = dt.strftime("%Y")
    year_month = dt.strftime("%Y-%m")
    day = dt.strftime("%d")
    filename = (
        f"{media_playback_id}_{_FORGE_DEFAULT_WIDTH}x{_FORGE_DEFAULT_HEIGHT}"
        f"_{_FORGE_DEFAULT_FPS}_{_FORGE_DEFAULT_BITRATE}K.mp4"
    )
    return f"{_FORGE_CDN_BASE_URL}/{year}/{year_month}/{day}/{filename}"


def _parse_single_item(item: dict[str, Any]) -> dict[str, Any]:
    content_id = str(item.get("id") or item.get("content_id") or item.get("mediaPlaybackId") or "")
    mp_list = item.get("mediaPlayback")
    mp = mp_list[0] if (isinstance(mp_list, list) and mp_list and isinstance(mp_list[0], dict)) else {}

    dt_val = _parse_date(item.get("gameDate") or mp.get("date") or item.get("date") or item.get("timestamp"))
    media_playback_id = str(mp.get("mediaPlaybackId") or item.get("mediaPlaybackId") or "")

    title = str(mp.get("title") or item.get("title") or item.get("headline") or "")
    blurb = str(mp.get("blurb") or mp.get("description") or item.get("blurb") or item.get("description") or "")

    parsed_fields = _parse_fields(item["fields"]) if isinstance(item.get("fields"), list) else {}

    player_id = parsed_fields.get("player_id") or item.get("player_id")
    player_name = parsed_fields.get("player_name") or item.get("player_name") or item.get("player")
    event_type = parsed_fields.get("event_type") or item.get("event_type") or item.get("event")
    exit_velocity = parsed_fields.get("exit_velocity")
    hit_distance = parsed_fields.get("hit_distance")

    raw_playbacks = item.get("playbacks") or mp.get("playbacks") or []
    playback_list, best_mp4_url, hls_url = _parse_playbacks(raw_playbacks)

    if not best_mp4_url and media_playback_id and dt_val is not None:
        forge_url = _build_forge_cdn_mp4_url(media_playback_id, dt_val)
        if forge_url:
            best_mp4_url = forge_url
            if not any(p.get("url") == forge_url for p in playback_list):
                playback_list.append(
                    {
                        "name": f"mp4 {_FORGE_DEFAULT_BITRATE}K",
                        "url": forge_url,
                        "bitrate": _FORGE_DEFAULT_BITRATE,
                        "width": _FORGE_DEFAULT_WIDTH,
                        "height": _FORGE_DEFAULT_HEIGHT,
                    }
                )

    return {
        "content_id": content_id,
        "date": dt_val,
        "title": title,
        "blurb": blurb,
        "player_id": int(player_id) if player_id is not None else None,
        "player_name": player_name,
        "event_type": event_type,
        "exit_velocity": exit_velocity,
        "hit_distance": hit_distance,
        "best_mp4_url": best_mp4_url,
        "hls_url": hls_url,
        "playbacks": playback_list,
    }


def parse_film_room_search(data: object) -> pl.DataFrame:
    """Parse Film Room GraphQL / REST search JSON response into a Polars DataFrame."""
    if not isinstance(data, dict):
        raise UpstreamParseError(f"Expected dict from Film Room search API, got {type(data)}")

    raw_items = _extract_raw_items(data)
    records = [_parse_single_item(item) for item in raw_items if isinstance(item, dict)]

    if not records:
        return pl.DataFrame(schema=FILM_ROOM_SCHEMA)

    return pl.DataFrame(records, schema=FILM_ROOM_SCHEMA)
