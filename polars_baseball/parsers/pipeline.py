import html
import json
import re
from typing import Any, cast

import lxml.etree
import polars as pl

from polars_baseball.exceptions import UpstreamStructureChangedError


def _parse_scouting_grades(bio_text: str) -> dict[str, int]:
    if not bio_text:
        return {}

    clean_text = re.sub(r"<[^>]+>", " ", bio_text)
    grades: dict[str, int] = {}
    pattern = r"(\b[A-Za-z0-9\-/\s]+)\s*:\s*(\d+)"
    matches = re.findall(pattern, clean_text)

    target_keys = {
        "hit",
        "power",
        "run",
        "arm",
        "field",
        "overall",
        "fastball",
        "slider",
        "curveball",
        "changeup",
        "cutter",
        "splitter",
        "control",
    }

    for k, v in matches:
        k_clean = k.strip().lower()
        if k_clean in target_keys:
            grades[k_clean] = int(v)
    return grades


def _resolve_player_row(item: dict[str, Any], payload: dict[str, Any]) -> dict[str, Any]:
    p_entity = item.get("playerEntity", {})
    player_ref = p_entity.get("player", {}).get("__ref")
    player_data: dict[str, Any] = payload.get(player_ref, {}) if player_ref else {}

    first_name = player_data.get("useName", "")
    last_name = player_data.get("useLastName", "")

    birth_city = player_data.get("birthCity", "")
    birth_country = player_data.get("birthCountry", "")
    birthplace = f"{birth_city}, {birth_country}".strip(", ")

    team_ref = player_data.get("activeRoster", {}).get("__ref")
    team_data: dict[str, Any] = payload.get(team_ref, {}) if team_ref else {}

    sport_ref = team_data.get("sport", {}).get("__ref")
    sport_data: dict[str, Any] = payload.get(sport_ref, {}) if sport_ref else {}

    bio_list = p_entity.get("prospectBio", [])
    grades: dict[str, int] = {}
    if bio_list:
        latest_bio = bio_list[-1]
        scouting_report = latest_bio.get("contentText", "")
        grades = _parse_scouting_grades(scouting_report)

    return {
        "rank": item.get("rank"),
        "player_id": player_data.get("id"),
        "name": f"{first_name} {last_name}".strip(),
        "position": p_entity.get("position"),
        "team": team_data.get("name"),
        "organization": team_data.get("parentOrgName"),
        "level": sport_data.get("abbreviation"),
        "age": player_data.get("currentAge"),
        "height": player_data.get("height"),
        "weight": player_data.get("weight"),
        "bats": player_data.get("batSideCode"),
        "throws": player_data.get("pitchHandCode"),
        "eta": p_entity.get("eta"),
        "signed": p_entity.get("signed"),
        "birth_date": player_data.get("birthDate"),
        "birthplace": birthplace,
        "grade_overall": grades.get("overall"),
        "grade_hit": grades.get("hit"),
        "grade_power": grades.get("power"),
        "grade_run": grades.get("run"),
        "grade_arm": grades.get("arm"),
        "grade_field": grades.get("field"),
        "grade_fastball": grades.get("fastball"),
        "grade_slider": grades.get("slider"),
        "grade_curveball": grades.get("curveball"),
        "grade_changeup": grades.get("changeup"),
        "grade_cutter": grades.get("cutter"),
        "grade_splitter": grades.get("splitter"),
        "grade_control": grades.get("control"),
    }


class MLBPipelineParser:
    def parse(self, raw_html: str) -> pl.DataFrame:
        html_parser = lxml.etree.HTMLParser()
        tree = lxml.etree.fromstring(raw_html.encode("utf-8"), html_parser)
        if tree is None:
            raise UpstreamStructureChangedError("Failed to parse HTML structure.")

        raw_states = tree.xpath("//span[@data-init-state]/@data-init-state")
        if not isinstance(raw_states, list) or not raw_states:
            raise UpstreamStructureChangedError("No data-init-state attribute found in HTML.")

        raw_state = raw_states[0]
        if not raw_state:
            raise UpstreamStructureChangedError("data-init-state attribute is empty.")

        try:
            # We cast to str because raw_state could technically be a list, but it's a string here
            state: dict[str, Any] = json.loads(html.unescape(cast(str, raw_state)))
        except json.JSONDecodeError as err:
            raise UpstreamStructureChangedError(f"Failed to parse data-init-state as JSON: {err}") from err

        payload = state.get("payload", {})
        root_query = payload.get("ROOT_QUERY", {})

        ranking_key = next((k for k in root_query.keys() if "getPlayerRankingsFromSelection" in k), None)
        if not ranking_key:
            raise UpstreamStructureChangedError("No player rankings data found in root query.")

        rankings = root_query[ranking_key]
        if not isinstance(rankings, list):
            raise UpstreamStructureChangedError("Player rankings data is not a list.")

        rows = [_resolve_player_row(item, payload) for item in rankings]
        return pl.DataFrame(rows)
