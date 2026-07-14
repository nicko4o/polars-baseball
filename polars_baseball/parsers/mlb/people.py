from typing import Any

from polars_baseball.parsers.mlb.types import PeopleAwardDict, PersonDict


def parse_person(person_data: dict[str, Any]) -> PersonDict:
    pos = person_data.get("primaryPosition", {})
    bat = person_data.get("batSide", {})
    pitch = person_data.get("pitchHand", {})
    return {
        "id": person_data.get("id"),
        "fullName": person_data.get("fullName"),
        "firstName": person_data.get("firstName"),
        "lastName": person_data.get("lastName"),
        "primaryNumber": person_data.get("primaryNumber"),
        "birthDate": person_data.get("birthDate"),
        "currentAge": person_data.get("currentAge"),
        "birthCity": person_data.get("birthCity"),
        "birthStateProvince": person_data.get("birthStateProvince"),
        "birthCountry": person_data.get("birthCountry"),
        "height": person_data.get("height"),
        "weight": person_data.get("weight"),
        "active": person_data.get("active"),
        "primaryPositionCode": pos.get("code"),
        "primaryPositionName": pos.get("name"),
        "primaryPositionAbbrev": pos.get("abbreviation"),
        "useName": person_data.get("useName"),
        "boxscoreName": person_data.get("boxscoreName"),
        "gender": person_data.get("gender"),
        "isPlayer": person_data.get("isPlayer"),
        "isVerified": person_data.get("isVerified"),
        "draftYear": person_data.get("draftYear"),
        "mlbDebutDate": person_data.get("mlbDebutDate"),
        "batSideCode": bat.get("code"),
        "pitchHandCode": pitch.get("code"),
    }


def parse_people_award(award_data: dict[str, Any], person_id: int) -> PeopleAwardDict:
    team = award_data.get("team", {})
    player = award_data.get("player", {})
    team_data = team if isinstance(team, dict) else {}
    player_data = player if isinstance(player, dict) else {}
    position = player_data.get("primaryPosition", {})
    position_data = position if isinstance(position, dict) else {}
    return {
        "personId": person_id,
        "awardId": award_data.get("id"),
        "awardName": award_data.get("name"),
        "date": award_data.get("date"),
        "season": award_data.get("season"),
        "teamId": team_data.get("id"),
        "teamName": team_data.get("teamName"),
        "positionCode": position_data.get("code"),
        "positionName": position_data.get("name"),
        "positionType": position_data.get("type"),
        "positionAbbreviation": position_data.get("abbreviation"),
    }
