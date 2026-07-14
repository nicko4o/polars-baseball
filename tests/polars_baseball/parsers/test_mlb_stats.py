from polars_baseball.parsers.mlb import (
    parse_game,
    parse_person,
    parse_player_stats,
)


def test_parse_person_flattens_nested_profile_fields() -> None:
    row = parse_person(
        {
            "id": 545361,
            "fullName": "Mike Trout",
            "primaryPosition": {"code": "8", "name": "Outfielder", "abbreviation": "CF"},
            "batSide": {"code": "R"},
            "pitchHand": {"code": "R"},
        }
    )

    assert row["id"] == 545361
    assert row["fullName"] == "Mike Trout"
    assert row["primaryPositionAbbrev"] == "CF"
    assert row["batSideCode"] == "R"
    assert row["pitchHandCode"] == "R"


def test_parse_game_flattens_schedule_team_fields() -> None:
    row = parse_game(
        {
            "gamePk": 715789,
            "season": "2026",
            "gameDate": "2026-04-01T23:10:00Z",
            "status": {"abstractGameState": "Preview", "statusCode": "S", "detailedState": "Scheduled"},
            "teams": {
                "away": {"score": 1, "team": {"id": 119, "name": "Los Angeles Dodgers"}},
                "home": {"score": 2, "team": {"id": 144, "name": "Atlanta Braves"}},
            },
            "venue": {"id": 4705, "name": "Truist Park"},
        }
    )

    assert row["gamePk"] == 715789
    assert row["awayTeamId"] == 119
    assert row["awayScore"] == 1
    assert row["homeTeamName"] == "Atlanta Braves"
    assert row["venueName"] == "Truist Park"


def test_parse_player_stats_preserves_dynamic_stat_columns() -> None:
    rows = parse_player_stats(
        {
            "stats": [
                {
                    "type": {"displayName": "season"},
                    "group": {"displayName": "hitting"},
                    "splits": [{"season": "2024", "stat": {"gamesPlayed": 150, "nested": {"skip": True}}}],
                }
            ]
        },
        person_id=545361,
        target_group="hitting",
        target_type="season",
    )

    assert rows == [{"personId": 545361, "season": 2024, "group": "hitting", "statType": "season", "gamesPlayed": 150}]
