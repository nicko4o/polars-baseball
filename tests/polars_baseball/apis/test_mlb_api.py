import json
from datetime import timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import polars as pl
import pytest

from polars_baseball._client import HttpClient
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
from polars_baseball.context import BaseballContext
from polars_baseball.exceptions import InvalidParameterError, PolarsBaseballTransportError, UpstreamParseError

# ── Mock Data ──────────────────────────────────────────────────────────
_MOCK_PEOPLE_JSON = {
    "people": [
        {
            "id": 545361,
            "fullName": "Mike Trout",
            "firstName": "Michael",
            "lastName": "Trout",
            "primaryNumber": "27",
            "birthDate": "1991-08-07",
            "currentAge": 34,
            "birthCity": "Vineland",
            "birthStateProvince": "NJ",
            "birthCountry": "USA",
            "height": "6' 2\"",
            "weight": 235,
            "active": True,
            "primaryPosition": {"code": "8", "name": "Outfielder", "type": "Outfielder", "abbreviation": "CF"},
            "useName": "Mike",
            "boxscoreName": "Trout",
            "gender": "M",
            "isPlayer": True,
            "isVerified": True,
            "draftYear": 2009,
            "mlbDebutDate": "2011-07-08",
            "batSide": {"code": "R"},
            "pitchHand": {"code": "R"},
        }
    ]
}

_MOCK_PEOPLE_AWARDS_JSON = {
    "awards": [
        {
            "id": "ALMVP",
            "name": "AL MVP",
            "date": "2021-11-18",
            "season": "2021",
            "team": {"id": 108, "teamName": "LA Angels"},
            "player": {
                "id": 660271,
                "primaryPosition": {
                    "code": "Y",
                    "name": "Two-Way Player",
                    "type": "Two-Way Player",
                    "abbreviation": "TWP",
                },
            },
        }
    ]
}

_MOCK_SCHEDULE_JSON = {
    "dates": [
        {
            "date": "2026-04-01",
            "games": [
                {
                    "gamePk": 715789,
                    "gameType": "R",
                    "season": "2026",
                    "gameDate": "2026-04-01T23:10:00Z",
                    "officialDate": "2026-04-01",
                    "status": {"abstractGameState": "Preview", "statusCode": "S", "detailedState": "Scheduled"},
                    "teams": {
                        "away": {
                            "score": 0,
                            "team": {"id": 119, "name": "Los Angeles Dodgers"},
                            "probablePitcher": {"id": 669022, "fullName": "Yoshinobu Yamamoto"},
                        },
                        "home": {
                            "score": 0,
                            "team": {"id": 144, "name": "Atlanta Braves"},
                            "probablePitcher": {"id": 675911, "fullName": "Spencer Strider"},
                        },
                    },
                    "venue": {"id": 4705, "name": "Truist Park"},
                    "doubleHeader": False,
                    "gamedayType": "P",
                    "tiebreaker": False,
                    "calendarEventID": "123-456",
                    "seasonDisplay": "2026",
                    "dayNight": "night",
                    "description": "Opening Day",
                    "scheduledInnings": 9,
                    "gamesInSeries": 3,
                    "seriesGameNumber": 1,
                    "seriesDescription": "Regular Season",
                    "linescore": {
                        "teams": {
                            "away": {"runs": 2, "hits": 5, "errors": 0},
                            "home": {"runs": 3, "hits": 7, "errors": 1},
                        }
                    },
                    "decisions": {
                        "winner": {"id": 675911, "fullName": "Spencer Strider"},
                        "loser": {"id": 669022, "fullName": "Yoshinobu Yamamoto"},
                        "save": {"id": 123456, "fullName": "Closer Name"},
                    },
                }
            ],
        }
    ]
}

_MOCK_ROSTER_JSON = {
    "roster": [
        {
            "person": {"id": 660271, "fullName": "Shohei Ohtani"},
            "jerseyNumber": "17",
            "position": {"code": "D", "name": "Designated Hitter", "type": "Hitter", "abbreviation": "DH"},
            "status": {"code": "A", "description": "Active"},
        }
    ]
}

_MOCK_PLAYER_STATS_JSON = {
    "stats": [
        {
            "type": {"displayName": "season"},
            "group": {"displayName": "hitting"},
            "splits": [{"season": "2024", "stat": {"gamesPlayed": 150, "homeRuns": 30, "strikeOuts": 100}}],
        }
    ]
}

_MOCK_BOXSCORE_JSON = {
    "teams": {
        "away": {
            "team": {"id": 119, "name": "Los Angeles Dodgers"},
            "players": {
                "ID545361": {
                    "person": {"id": 545361, "fullName": "Mike Trout"},
                    "jerseyNumber": "27",
                    "position": {"code": "8", "name": "Outfielder", "abbreviation": "CF"},
                    "battingOrder": "100",
                    "stats": {
                        "batting": {
                            "atBats": 4,
                            "runs": 1,
                            "hits": 2,
                            "doubles": 0,
                            "triples": 0,
                            "homeRuns": 1,
                            "rbi": 2,
                            "baseOnBalls": 1,
                            "strikeOuts": 1,
                            "leftOnBase": 3,
                            "groundIntoDoublePlay": 0,
                            "stolenBases": 1,
                            "caughtStealing": 0,
                        },
                        "pitching": {},
                        "fielding": {"putOuts": 3, "errors": 0},
                    },
                }
            },
        },
        "home": {
            "team": {"id": 144, "name": "Atlanta Braves"},
            "players": {
                "ID660271": {
                    "person": {"id": 660271, "fullName": "Shohei Ohtani"},
                    "jerseyNumber": "17",
                    "position": {"code": "D", "name": "Designated Hitter", "abbreviation": "DH"},
                    "stats": {
                        "batting": {"atBats": 4, "runs": 0},
                        "pitching": {
                            "inningsPitched": "5.2",
                            "hits": 3,
                            "runs": 0,
                            "earnedRuns": 0,
                            "baseOnBalls": 2,
                            "strikeOuts": 7,
                            "homeRuns": 0,
                            "outs": 17,
                        },
                        "fielding": {},
                    },
                }
            },
        },
    }
}


# ── Unit Tests ─────────────────────────────────────────────────────────
@pytest.mark.asyncio
@patch("polars_baseball.apis.mlb.people.default_context")
async def test_mlb_people_basic(mock_default_ctx: MagicMock) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=json.dumps(_MOCK_PEOPLE_JSON))
    mock_default_ctx.return_value = BaseballContext(http=mock_http)

    df = await mlb_people(person_ids=545361)
    assert isinstance(df, pl.DataFrame)
    assert df.height == 1
    assert df["id"][0] == 545361
    assert df["fullName"][0] == "Mike Trout"
    assert df["active"][0] is True
    assert df["primaryPositionAbbrev"][0] == "CF"
    assert df["batSideCode"][0] == "R"


@pytest.mark.asyncio
async def test_mlb_people_invalid_parameters() -> None:
    with pytest.raises(InvalidParameterError, match="must not be empty"):
        await mlb_people(person_ids=[])

    with pytest.raises(InvalidParameterError, match="Must be positive integer"):
        await mlb_people(person_ids=-5)

    with pytest.raises(InvalidParameterError, match="Must be positive integer"):
        await mlb_people(person_ids=[545361, -10])


@pytest.mark.asyncio
@patch("polars_baseball.apis.mlb.people.default_context")
async def test_mlb_people_awards_basic(mock_default_ctx: MagicMock) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=json.dumps(_MOCK_PEOPLE_AWARDS_JSON))
    mock_default_ctx.return_value = BaseballContext(http=mock_http)

    df = await mlb_people_awards(person_id=660271)
    assert isinstance(df, pl.DataFrame)
    assert df.height == 1
    assert df["personId"][0] == 660271
    assert df["awardId"][0] == "ALMVP"
    assert df["awardName"][0] == "AL MVP"
    assert df["season"][0] == 2021
    assert df["teamId"][0] == 108
    assert df["positionAbbreviation"][0] == "TWP"


@pytest.mark.asyncio
@patch("polars_baseball.apis.mlb.people.default_context")
async def test_mlb_people_awards_empty(mock_default_ctx: MagicMock) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=json.dumps({"awards": []}))
    mock_default_ctx.return_value = BaseballContext(http=mock_http)

    df = await mlb_people_awards(person_id=660271)
    assert isinstance(df, pl.DataFrame)
    assert df.is_empty()


@pytest.mark.asyncio
async def test_mlb_people_awards_invalid_params() -> None:
    with pytest.raises(InvalidParameterError, match="person_id must be a positive integer"):
        await mlb_people_awards(person_id=0)


@pytest.mark.asyncio
@patch("polars_baseball.apis.mlb.schedule.default_context")
async def test_mlb_schedule_basic(mock_default_ctx: MagicMock) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=json.dumps(_MOCK_SCHEDULE_JSON))
    mock_default_ctx.return_value = BaseballContext(http=mock_http)

    df = await mlb_schedule(season=2026)
    assert isinstance(df, pl.DataFrame)
    assert df.height == 1
    assert df["gamePk"][0] == 715789
    assert df["awayTeamName"][0] == "Los Angeles Dodgers"
    assert df["homeTeamName"][0] == "Atlanta Braves"
    assert df["venueName"][0] == "Truist Park"
    assert df["scheduledInnings"][0] == 9
    assert df["awayHits"][0] == 5
    assert df["awayErrors"][0] == 0
    assert df["homeHits"][0] == 7
    assert df["homeErrors"][0] == 1
    assert df["winnerPitcherId"][0] == 675911
    assert df["winnerPitcherName"][0] == "Spencer Strider"
    assert df["loserPitcherId"][0] == 669022
    assert df["loserPitcherName"][0] == "Yoshinobu Yamamoto"
    assert df["savePitcherId"][0] == 123456
    assert df["savePitcherName"][0] == "Closer Name"


@pytest.mark.asyncio
@patch("polars_baseball.apis.mlb.schedule.default_context")
async def test_mlb_schedule_with_hydrate_probable_pitchers(mock_default_ctx: MagicMock) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=json.dumps(_MOCK_SCHEDULE_JSON))
    mock_default_ctx.return_value = BaseballContext(http=mock_http)

    df = await mlb_schedule(season=2026, hydrate="probablePitcher")

    assert df["awayProbablePitcherId"][0] == 669022
    assert df["awayProbablePitcherName"][0] == "Yoshinobu Yamamoto"
    assert df["homeProbablePitcherId"][0] == 675911
    assert df["homeProbablePitcherName"][0] == "Spencer Strider"
    mock_http.get_text.assert_awaited_once()
    await_args = mock_http.get_text.await_args
    assert await_args is not None
    params = await_args.kwargs["params"]
    assert params["hydrate"] == "probablePitcher"


@pytest.mark.asyncio
async def test_mlb_schedule_invalid_parameters() -> None:
    with pytest.raises(InvalidParameterError, match="Either season or date must be provided"):
        await mlb_schedule()

    with pytest.raises(InvalidParameterError, match="Invalid season"):
        await mlb_schedule(season=1800)

    with pytest.raises(InvalidParameterError, match="date must be in YYYY-MM-DD format"):
        await mlb_schedule(date="04-01-2026")

    with pytest.raises(InvalidParameterError, match="positive integer"):
        await mlb_schedule(season=2026, team_id=-1)


@pytest.mark.asyncio
@patch("polars_baseball.apis.mlb.roster.default_context")
async def test_mlb_roster_basic(mock_default_ctx: MagicMock) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=json.dumps(_MOCK_ROSTER_JSON))
    mock_default_ctx.return_value = BaseballContext(http=mock_http)

    df = await mlb_roster(team_id=119, season=2026)
    assert isinstance(df, pl.DataFrame)
    assert df.height == 1
    assert df["teamId"][0] == 119
    assert df["personId"][0] == 660271
    assert df["fullName"][0] == "Shohei Ohtani"
    assert df["jerseyNumber"][0] == "17"
    assert df["positionAbbrev"][0] == "DH"


@pytest.mark.asyncio
async def test_mlb_roster_invalid_parameters() -> None:
    with pytest.raises(InvalidParameterError, match="positive integer"):
        await mlb_roster(team_id=0)

    with pytest.raises(InvalidParameterError, match="Invalid season"):
        await mlb_roster(team_id=119, season=1800)

    with pytest.raises(InvalidParameterError, match="roster_type must be a non-empty string"):
        await mlb_roster(team_id=119, roster_type="")


@pytest.mark.asyncio
@patch("polars_baseball.apis.mlb.people.default_context")
async def test_mlb_api_upstream_error(mock_default_ctx: MagicMock) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(side_effect=PolarsBaseballTransportError("Connection reset"))
    mock_default_ctx.return_value = BaseballContext(http=mock_http)

    with pytest.raises(PolarsBaseballTransportError, match="Connection reset"):
        await mlb_people(person_ids=545361)


@pytest.mark.asyncio
@patch("polars_baseball.apis.mlb.stats.default_context")
async def test_mlb_player_stats_basic(mock_default_ctx: MagicMock) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=json.dumps(_MOCK_PLAYER_STATS_JSON))
    mock_default_ctx.return_value = BaseballContext(http=mock_http)

    df = await mlb_player_stats(person_id=545361, group="hitting", stats_type="season", season=2024)
    assert isinstance(df, pl.DataFrame)
    assert df.height == 1
    assert df["personId"][0] == 545361
    assert df["season"][0] == 2024
    assert df["group"][0] == "hitting"
    assert df["statType"][0] == "season"
    assert df["gamesPlayed"][0] == 150
    assert df["homeRuns"][0] == 30
    assert df["strikeOuts"][0] == 100


@pytest.mark.asyncio
async def test_mlb_player_stats_invalid_parameters() -> None:
    with pytest.raises(InvalidParameterError, match="person_id must be a positive integer"):
        await mlb_player_stats(person_id=-1, group="hitting")

    with pytest.raises(InvalidParameterError, match="group must be a non-empty string"):
        await mlb_player_stats(person_id=545361, group="")

    with pytest.raises(InvalidParameterError, match="stats_type must be a non-empty string"):
        await mlb_player_stats(person_id=545361, group="hitting", stats_type="")

    with pytest.raises(InvalidParameterError, match="Invalid season"):
        await mlb_player_stats(person_id=545361, group="hitting", season=1800)

    with pytest.raises(InvalidParameterError, match="start_date must be in YYYY-MM-DD format"):
        await mlb_player_stats(person_id=545361, group="hitting", start_date="2026/04/01")

    with pytest.raises(InvalidParameterError, match="end_date must be in YYYY-MM-DD format"):
        await mlb_player_stats(person_id=545361, group="hitting", end_date="2026-04-3")


@pytest.mark.asyncio
@patch("polars_baseball.apis.mlb.stats.default_context")
async def test_mlb_player_stats_with_dates(mock_default_ctx: MagicMock) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=json.dumps(_MOCK_PLAYER_STATS_JSON))
    mock_default_ctx.return_value = BaseballContext(http=mock_http)

    df = await mlb_player_stats(
        person_id=545361,
        group="hitting",
        stats_type="season",
        start_date="2026-04-01",
        end_date="2026-04-30",
    )
    assert isinstance(df, pl.DataFrame)
    assert df.height == 1
    mock_http.get_text.assert_awaited_once()
    await_args = mock_http.get_text.await_args
    assert await_args is not None
    params = await_args.kwargs["params"]
    assert params["startDate"] == "2026-04-01"
    assert params["endDate"] == "2026-04-30"


@pytest.mark.asyncio
@patch("polars_baseball.apis.mlb.game.default_context")
async def test_mlb_game_boxscore_basic(mock_default_ctx: MagicMock) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=json.dumps(_MOCK_BOXSCORE_JSON))
    mock_default_ctx.return_value = BaseballContext(http=mock_http)

    df = await mlb_game_boxscore(game_pk=715789)
    assert isinstance(df, pl.DataFrame)
    assert df.height == 2
    # Check away team player
    away_player = df.filter(pl.col("personId") == 545361)
    assert away_player.height == 1
    assert away_player["teamId"][0] == 119
    assert away_player["fullName"][0] == "Mike Trout"
    assert away_player["batting_runs"][0] == 1
    assert away_player["batting_homeRuns"][0] == 1
    assert away_player["fielding_putOuts"][0] == 3

    # Check home team player
    home_player = df.filter(pl.col("personId") == 660271)
    assert home_player.height == 1
    assert home_player["teamId"][0] == 144
    assert home_player["fullName"][0] == "Shohei Ohtani"
    assert home_player["batting_runs"][0] == 0
    assert home_player["pitching_runs"][0] == 0


@pytest.mark.asyncio
@patch("polars_baseball.apis.mlb.game.default_context")
async def test_mlb_game_boxscore_stats_schema(mock_default_ctx: MagicMock) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=json.dumps(_MOCK_BOXSCORE_JSON))
    mock_default_ctx.return_value = BaseballContext(http=mock_http)

    df = await mlb_game_boxscore_stats(game_pk=715789)

    assert df.schema["batting_atBats"] == pl.Int64
    assert df.schema["pitching_inningsPitched"] == pl.String
    assert df.schema["fielding_errors"] == pl.Int64
    assert df.schema["isInBattingOrder"] == pl.Boolean
    assert df.schema["battingOrder"] == pl.Int64

    away_player = df.filter(pl.col("personId") == 545361)
    assert away_player["batting_atBats"][0] == 4
    assert away_player["batting_hits"][0] == 2
    assert away_player["fielding_errors"][0] == 0
    assert away_player["isInBattingOrder"][0] is True
    assert away_player["battingOrder"][0] == 100

    home_player = df.filter(pl.col("personId") == 660271)
    assert home_player["pitching_inningsPitched"][0] == "5.2"
    assert home_player["pitching_strikeOuts"][0] == 7
    assert home_player["isInBattingOrder"][0] is False


@pytest.mark.asyncio
async def test_mlb_game_boxscore_invalid_parameters() -> None:
    with pytest.raises(InvalidParameterError, match="game_pk must be a positive integer"):
        await mlb_game_boxscore(game_pk=-1)


# ── Teams ─────────────────────────────────────────────────────────────────
_MOCK_TEAMS_JSON = {
    "teams": [
        {
            "id": 119,
            "name": "Los Angeles Dodgers",
            "abbreviation": "LAD",
            "teamName": "Dodgers",
            "locationName": "Los Angeles",
            "league": {"id": 104, "name": "National League"},
            "division": {"id": 203, "name": "National League West"},
            "venue": {"id": 22, "name": "Dodger Stadium"},
            "springLeague": {"name": "Cactus League"},
        },
        {
            "id": 147,
            "name": "New York Yankees",
            "abbreviation": "NYY",
            "teamName": "Yankees",
            "locationName": "Bronx",
            "league": {"id": 103, "name": "American League"},
            "division": {"id": 201, "name": "American League East"},
            "venue": {"id": 3313, "name": "Yankee Stadium"},
            "springLeague": {"name": "Grapefruit League"},
        },
    ]
}


@pytest.mark.asyncio
@patch("polars_baseball.apis.mlb.taxonomy.default_context")
async def test_mlb_teams_basic(mock_default_ctx: MagicMock) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=json.dumps(_MOCK_TEAMS_JSON))
    mock_default_ctx.return_value = BaseballContext(http=mock_http)

    df = await mlb_teams(season=2025)
    assert isinstance(df, pl.DataFrame)
    assert df.height == 2
    dodgers = df.filter(pl.col("id") == 119)
    assert dodgers["name"][0] == "Los Angeles Dodgers"
    assert dodgers["abbreviation"][0] == "LAD"
    assert dodgers["leagueId"][0] == 104
    assert dodgers["divisionName"][0] == "National League West"


@pytest.mark.asyncio
@patch("polars_baseball.apis.mlb.taxonomy.default_context")
async def test_mlb_teams_empty(mock_default_ctx: MagicMock) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=json.dumps({"teams": []}))
    mock_default_ctx.return_value = BaseballContext(http=mock_http)

    df = await mlb_teams(season=2025)
    assert isinstance(df, pl.DataFrame)
    assert df.is_empty()


@pytest.mark.asyncio
@patch("polars_baseball.apis.mlb.taxonomy.default_context")
async def test_mlb_teams_upstream_error(mock_default_ctx: MagicMock) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(side_effect=PolarsBaseballTransportError("API timeout"))
    mock_default_ctx.return_value = BaseballContext(http=mock_http)

    with pytest.raises(PolarsBaseballTransportError, match="API timeout"):
        await mlb_teams(season=2025)


@pytest.mark.asyncio
async def test_mlb_teams_invalid_params() -> None:
    with pytest.raises(InvalidParameterError, match="season must be a positive integer"):
        await mlb_teams(season=0)
    with pytest.raises(InvalidParameterError, match="Invalid season"):
        await mlb_teams(season=1800)


# ── Divisions and Leagues ──────────────────────────────────────────────────
_MOCK_DIVISIONS_JSON = {
    "divisions": [
        {
            "id": 201,
            "name": "American League East",
            "season": "2026",
            "nameShort": "AL East",
            "abbreviation": "ALE",
            "league": {"id": 103},
            "sport": {"id": 1},
            "hasWildcard": False,
            "sortOrder": 22,
            "numPlayoffTeams": 1,
            "active": True,
        }
    ]
}

_MOCK_LEAGUES_JSON = {
    "leagues": [
        {
            "id": 103,
            "name": "American League",
            "nameShort": "American",
            "abbreviation": "AL",
            "orgCode": "AL",
            "season": "2026",
            "seasonState": "inseason",
            "active": True,
            "sport": {"id": 1},
            "numTeams": 15,
            "numGames": 162,
            "numWildcardTeams": 3,
            "hasWildCard": True,
            "divisionsInUse": True,
            "sortOrder": 21,
        }
    ]
}


@pytest.mark.asyncio
@patch("polars_baseball.apis.mlb.taxonomy.default_context")
async def test_mlb_divisions_basic(mock_default_ctx: MagicMock) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=json.dumps(_MOCK_DIVISIONS_JSON))
    mock_default_ctx.return_value = BaseballContext(http=mock_http)

    df = await mlb_divisions()
    assert isinstance(df, pl.DataFrame)
    assert df.height == 1
    assert df["id"][0] == 201
    assert df["name"][0] == "American League East"
    assert df["leagueId"][0] == 103
    assert df["sportId"][0] == 1
    assert df["active"][0] is True


@pytest.mark.asyncio
@patch("polars_baseball.apis.mlb.taxonomy.default_context")
async def test_mlb_divisions_empty(mock_default_ctx: MagicMock) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=json.dumps({"divisions": []}))
    mock_default_ctx.return_value = BaseballContext(http=mock_http)

    df = await mlb_divisions()
    assert isinstance(df, pl.DataFrame)
    assert df.is_empty()


@pytest.mark.asyncio
async def test_mlb_divisions_invalid_params() -> None:
    with pytest.raises(InvalidParameterError, match="sport_id must be a positive integer"):
        await mlb_divisions(sport_id=0)


@pytest.mark.asyncio
@patch("polars_baseball.apis.mlb.taxonomy.default_context")
async def test_mlb_leagues_basic(mock_default_ctx: MagicMock) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=json.dumps(_MOCK_LEAGUES_JSON))
    mock_default_ctx.return_value = BaseballContext(http=mock_http)

    df = await mlb_leagues()
    assert isinstance(df, pl.DataFrame)
    assert df.height == 1
    assert df["id"][0] == 103
    assert df["name"][0] == "American League"
    assert df["sportId"][0] == 1
    assert df["numTeams"][0] == 15
    assert df["hasWildCard"][0] is True


@pytest.mark.asyncio
@patch("polars_baseball.apis.mlb.taxonomy.default_context")
async def test_mlb_leagues_empty(mock_default_ctx: MagicMock) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=json.dumps({"leagues": []}))
    mock_default_ctx.return_value = BaseballContext(http=mock_http)

    df = await mlb_leagues()
    assert isinstance(df, pl.DataFrame)
    assert df.is_empty()


@pytest.mark.asyncio
async def test_mlb_leagues_invalid_params() -> None:
    with pytest.raises(InvalidParameterError, match="sport_id must be a positive integer"):
        await mlb_leagues(sport_id=0)


# ── Play-by-Play ──────────────────────────────────────────────────────────
_MOCK_PBP_JSON = {
    "allPlays": [
        {
            "atBatIndex": 0,
            "playEvents": [{"details": {"description": "Ball", "event": "Ball", "eventType": "ball"}}],
            "result": {
                "description": "Shohei Ohtani singles on a line drive.",
                "event": "Single",
                "eventType": "single",
                "rbi": 0,
                "awayScore": 0,
                "homeScore": 0,
            },
            "about": {"atBatIndex": 0, "halfInning": "top", "inning": 1},
            "count": {"balls": 1, "strikes": 0, "outs": 0},
            "matchup": {
                "batter": {"id": 660271, "fullName": "Shohei Ohtani"},
                "pitcher": {"id": 605151, "fullName": "Gerrit Cole"},
            },
        }
    ]
}


@pytest.mark.asyncio
@patch("polars_baseball.apis.mlb.game.default_context")
async def test_mlb_game_play_by_play_basic(mock_default_ctx: MagicMock) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=json.dumps(_MOCK_PBP_JSON))
    mock_default_ctx.return_value = BaseballContext(http=mock_http)

    df = await mlb_game_play_by_play(game_pk=715789)
    assert isinstance(df, pl.DataFrame)
    assert df.height == 1
    assert df["gamePk"][0] == 715789
    assert df["atBatIndex"][0] == 0
    assert df["batterId"][0] == 660271
    assert df["batterName"][0] == "Shohei Ohtani"
    assert df["pitcherName"][0] == "Gerrit Cole"
    assert df["event"][0] == "Single"
    assert df["inning"][0] == 1
    assert df["halfInning"][0] == "top"
    assert df["balls"][0] == 1
    assert df["strikes"][0] == 0
    assert df["outs"][0] == 0
    assert df["rbi"][0] == 0


@pytest.mark.asyncio
@patch("polars_baseball.apis.mlb.game.default_context")
async def test_mlb_game_play_by_play_empty(mock_default_ctx: MagicMock) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=json.dumps({"allPlays": []}))
    mock_default_ctx.return_value = BaseballContext(http=mock_http)

    df = await mlb_game_play_by_play(game_pk=715789)
    assert isinstance(df, pl.DataFrame)
    assert df.is_empty()


@pytest.mark.asyncio
@patch("polars_baseball.apis.mlb.game.default_context")
async def test_mlb_game_play_by_play_upstream_error(mock_default_ctx: MagicMock) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(side_effect=PolarsBaseballTransportError("Bad Gateway"))
    mock_default_ctx.return_value = BaseballContext(http=mock_http)

    with pytest.raises(PolarsBaseballTransportError, match="Bad Gateway"):
        await mlb_game_play_by_play(game_pk=715789)


@pytest.mark.asyncio
async def test_mlb_game_play_by_play_invalid_params() -> None:
    with pytest.raises(InvalidParameterError, match="game_pk must be a positive integer"):
        await mlb_game_play_by_play(game_pk=-1)


_MOCK_WP_JSON = [
    {
        "atBatIndex": 0,
        "result": {
            "description": "Shohei Ohtani singles on a line drive.",
            "event": "Single",
            "eventType": "single",
            "rbi": 0,
            "awayScore": 0,
            "homeScore": 0,
        },
        "about": {"atBatIndex": 0, "halfInning": "top", "inning": 1},
        "count": {"balls": 1, "strikes": 0, "outs": 0},
        "matchup": {
            "batter": {"id": 660271, "fullName": "Shohei Ohtani"},
            "pitcher": {"id": 605151, "fullName": "Gerrit Cole"},
        },
        "homeTeamWinProbability": 52.3,
        "awayTeamWinProbability": 47.7,
        "homeTeamWinProbabilityAdded": 3.1,
        "leverageIndex": 1.45,
        "dramaIndex": 22.0,
    }
]


@pytest.mark.asyncio
@patch("polars_baseball.apis.mlb.game.default_context")
async def test_mlb_game_play_by_play_with_win_probability(mock_default_ctx: MagicMock) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=json.dumps(_MOCK_WP_JSON))
    mock_default_ctx.return_value = BaseballContext(http=mock_http)

    df = await mlb_game_play_by_play(game_pk=715789, win_probability=True)
    assert isinstance(df, pl.DataFrame)
    assert df.height == 1
    assert df["homeTeamWinProbability"][0] == 52.3
    assert df["awayTeamWinProbability"][0] == 47.7
    assert df["homeTeamWinProbabilityAdded"][0] == 3.1
    assert df["leverageIndex"][0] == 1.45
    assert df["dramaIndex"][0] == 22.0
    assert df["rbi"][0] == 0
    assert df["batterName"][0] == "Shohei Ohtani"


@pytest.mark.asyncio
@patch("polars_baseball.apis.mlb.game.default_context")
async def test_mlb_game_win_probability_public_api(mock_default_ctx: MagicMock) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=json.dumps(_MOCK_WP_JSON))
    mock_default_ctx.return_value = BaseballContext(http=mock_http)

    df = await mlb_game_win_probability(game_pk=715789)

    assert isinstance(df, pl.DataFrame)
    assert df.height == 1
    assert df["homeTeamWinProbabilityAdded"][0] == 3.1
    assert df["batterId"][0] == 660271
    assert df["pitcherId"][0] == 605151


@pytest.mark.asyncio
async def test_mlb_game_win_probability_invalid_parameters() -> None:
    with pytest.raises(InvalidParameterError, match="game_pk must be a positive integer"):
        await mlb_game_win_probability(game_pk=-1)


@pytest.mark.asyncio
@patch("polars_baseball.apis.mlb.game.default_context")
async def test_mlb_game_play_by_play_with_win_probability_empty(
    mock_default_ctx: MagicMock,
) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=json.dumps([]))
    mock_default_ctx.return_value = BaseballContext(http=mock_http)

    df = await mlb_game_play_by_play(game_pk=715789, win_probability=True)
    assert isinstance(df, pl.DataFrame)
    assert df.is_empty()


# ── Stat Leaders ──────────────────────────────────────────────────────────
_MOCK_LEADERS_JSON = {
    "leagueLeaders": [
        {
            "leaderCategory": "homeRuns",
            "leaders": [
                {
                    "rank": 1,
                    "person": {"id": 660271, "fullName": "Shohei Ohtani"},
                    "team": {"id": 119, "name": "Los Angeles Dodgers"},
                    "league": {"id": 104},
                    "value": 48.0,
                }
            ],
        }
    ]
}


@pytest.mark.asyncio
@patch("polars_baseball.apis.mlb.stats.default_context")
async def test_mlb_stat_leaders_basic(mock_default_ctx: MagicMock) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=json.dumps(_MOCK_LEADERS_JSON))
    mock_default_ctx.return_value = BaseballContext(http=mock_http)

    df = await mlb_stat_leaders(season=2025, categories=["homeRuns"])
    assert isinstance(df, pl.DataFrame)
    assert df.height == 1
    assert df["personId"][0] == 660271
    assert df["personName"][0] == "Shohei Ohtani"
    assert df["teamName"][0] == "Los Angeles Dodgers"
    assert df["category"][0] == "homeRuns"
    assert df["rank"][0] == 1
    assert df["value"][0] == 48.0


@pytest.mark.asyncio
@patch("polars_baseball.apis.mlb.stats.default_context")
async def test_mlb_stat_leaders_empty(mock_default_ctx: MagicMock) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=json.dumps({"leagueLeaders": []}))
    mock_default_ctx.return_value = BaseballContext(http=mock_http)

    df = await mlb_stat_leaders(season=2025, categories=["homeRuns"])
    assert isinstance(df, pl.DataFrame)
    assert df.is_empty()


@pytest.mark.asyncio
@patch("polars_baseball.apis.mlb.stats.default_context")
async def test_mlb_stat_leaders_upstream_error(mock_default_ctx: MagicMock) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(side_effect=PolarsBaseballTransportError("Server Error"))
    mock_default_ctx.return_value = BaseballContext(http=mock_http)

    with pytest.raises(PolarsBaseballTransportError, match="Server Error"):
        await mlb_stat_leaders(season=2025, categories=["homeRuns"])


@pytest.mark.asyncio
async def test_mlb_stat_leaders_invalid_params() -> None:
    with pytest.raises(InvalidParameterError, match="Invalid season"):
        await mlb_stat_leaders(season=1800, categories=["homeRuns"])
    with pytest.raises(InvalidParameterError, match="categories must not be empty"):
        await mlb_stat_leaders(season=2025, categories=[])
    with pytest.raises(InvalidParameterError, match="limit must be a positive integer"):
        await mlb_stat_leaders(season=2025, categories=["homeRuns"], limit=0)


# ── Team Stats ──────────────────────────────────────────────────────────────
_MOCK_TEAM_STATS_JSON = {
    "stats": [
        {
            "type": {"displayName": "season"},
            "group": {"displayName": "hitting"},
            "splits": [
                {
                    "season": "2025",
                    "stat": {"gamesPlayed": 162, "runs": 850, "homeRuns": 233, "avg": 0.258},
                }
            ],
        }
    ]
}


@pytest.mark.asyncio
@patch("polars_baseball.apis.mlb.stats.default_context")
async def test_mlb_team_stats_basic(mock_default_ctx: MagicMock) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=json.dumps(_MOCK_TEAM_STATS_JSON))
    mock_default_ctx.return_value = BaseballContext(http=mock_http)

    df = await mlb_team_stats(team_id=119, season=2025, group="hitting")
    assert isinstance(df, pl.DataFrame)
    assert df.height == 1
    assert df["teamId"][0] == 119
    assert df["season"][0] == 2025
    assert df["group"][0] == "hitting"
    assert df["statType"][0] == "season"
    assert df["gamesPlayed"][0] == 162
    assert df["homeRuns"][0] == 233


@pytest.mark.asyncio
@patch("polars_baseball.apis.mlb.stats.default_context")
async def test_mlb_team_stats_empty(mock_default_ctx: MagicMock) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=json.dumps({"stats": []}))
    mock_default_ctx.return_value = BaseballContext(http=mock_http)

    df = await mlb_team_stats(team_id=119, season=2025)
    assert isinstance(df, pl.DataFrame)
    assert df.is_empty()


@pytest.mark.asyncio
async def test_mlb_team_stats_invalid_params() -> None:
    with pytest.raises(InvalidParameterError, match="team_id must be a positive integer"):
        await mlb_team_stats(team_id=-1, season=2025)
    with pytest.raises(InvalidParameterError, match="Invalid season"):
        await mlb_team_stats(team_id=119, season=1800)
    with pytest.raises(InvalidParameterError, match="group must be a non-empty string"):
        await mlb_team_stats(team_id=119, season=2025, group="")


# ── Postseason Schedule ─────────────────────────────────────────────────────
_MOCK_POSTSEASON_JSON = {
    "dates": [
        {
            "date": "2025-10-01",
            "games": [
                {
                    "gamePk": 715790,
                    "gameType": "P",
                    "season": "2025",
                    "gameDate": "2025-10-01T20:00:00Z",
                    "officialDate": "2025-10-01",
                    "status": {"abstractGameState": "Preview", "statusCode": "S", "detailedState": "Scheduled"},
                    "teams": {
                        "away": {"score": 0, "team": {"id": 119, "name": "Los Angeles Dodgers"}},
                        "home": {"score": 0, "team": {"id": 147, "name": "New York Yankees"}},
                    },
                    "venue": {"id": 1, "name": "Dodger Stadium"},
                    "doubleHeader": "N",
                    "gamedayType": "P",
                    "tiebreaker": "N",
                    "calendarEventID": "789-012",
                    "seasonDisplay": "2025",
                    "dayNight": "night",
                    "description": "World Series Game 1",
                    "scheduledInnings": 9,
                    "gamesInSeries": 7,
                    "seriesGameNumber": 1,
                    "seriesDescription": "World Series",
                }
            ],
        }
    ]
}


@pytest.mark.asyncio
@patch("polars_baseball.apis.mlb.schedule.default_context")
async def test_mlb_postseason_schedule_basic(mock_default_ctx: MagicMock) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=json.dumps(_MOCK_POSTSEASON_JSON))
    mock_default_ctx.return_value = BaseballContext(http=mock_http)

    df = await mlb_postseason_schedule(season=2025)
    assert isinstance(df, pl.DataFrame)
    assert df.height == 1
    assert df["gamePk"][0] == 715790
    assert df["gameType"][0] == "P"
    assert df["seriesDescription"][0] == "World Series"
    assert df["awayTeamName"][0] == "Los Angeles Dodgers"
    assert df["homeTeamName"][0] == "New York Yankees"


@pytest.mark.asyncio
@patch("polars_baseball.apis.mlb.schedule.default_context")
async def test_mlb_postseason_schedule_empty(mock_default_ctx: MagicMock) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=json.dumps({"dates": []}))
    mock_default_ctx.return_value = BaseballContext(http=mock_http)

    df = await mlb_postseason_schedule(season=2025)
    assert isinstance(df, pl.DataFrame)
    assert df.is_empty()


@pytest.mark.asyncio
async def test_mlb_postseason_schedule_invalid_params() -> None:
    with pytest.raises(InvalidParameterError, match="Invalid season"):
        await mlb_postseason_schedule(season=1800)


_MOCK_DRAFT_JSON = {
    "drafts": {
        "rounds": [
            {
                "round": "1",
                "picks": [
                    {
                        "pickRound": "1",
                        "pickNumber": 1,
                        "roundPickNumber": 1,
                        "person": {"id": 660271, "fullName": "Adley Rutschman"},
                        "team": {"id": 110, "name": "Baltimore Orioles"},
                        "signingBonus": 8100000,
                        "homeSchool": {"name": "Oregon State"},
                    },
                    {
                        "pickRound": "1",
                        "pickNumber": 2,
                        "roundPickNumber": 2,
                        "person": {"id": 677951, "fullName": "Bobby Witt Jr."},
                        "team": {"id": 118, "name": "Kansas City Royals"},
                        "signingBonus": 7790000,
                        "homeSchool": {"name": "Colleyville Heritage HS"},
                    },
                ],
            }
        ]
    }
}


@pytest.mark.asyncio
@patch("polars_baseball.apis.mlb.draft.default_context")
async def test_mlb_draft_basic(mock_default_ctx: MagicMock) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=json.dumps(_MOCK_DRAFT_JSON))
    mock_default_ctx.return_value = BaseballContext(http=mock_http)

    # 1. Fetch entire draft
    df = await mlb_draft(year=2019)
    assert isinstance(df, pl.DataFrame)
    assert df.height == 2
    assert df["year"][0] == 2019
    assert df["round"][0] == "1"
    assert df["pickNumber"][0] == 1
    assert df["playerName"][0] == "Adley Rutschman"
    assert df["teamName"][0] == "Baltimore Orioles"
    assert df["signingBonus"][0] == 8100000
    assert df["homeSchool"][0] == "Oregon State"

    # 2. Filter by draft round
    df_r1 = await mlb_draft(year=2019, draft_round=1)
    assert df_r1.height == 2

    # 3. Filter by team
    df_team = await mlb_draft(year=2019, team_id=118)
    assert df_team.height == 1
    assert df_team["playerName"][0] == "Bobby Witt Jr."


@pytest.mark.asyncio
async def test_mlb_draft_invalid_params() -> None:
    with pytest.raises(InvalidParameterError, match="Invalid draft season"):
        await mlb_draft(year=1800)
    with pytest.raises(InvalidParameterError, match="draft_round must be a positive integer"):
        await mlb_draft(year=2019, draft_round=0)
    with pytest.raises(InvalidParameterError, match="team_id must be a positive integer"):
        await mlb_draft(year=2019, team_id=-5)


_MOCK_PITCH_ARSENAL_JSON = {
    "stats": [
        {
            "type": {"displayName": "pitchArsenal"},
            "splits": [
                {
                    "stat": {
                        "type": {"code": "FF", "description": "Four-Seam Fastball"},
                        "percentage": 50.5,
                        "averageSpeed": 95.2,
                    }
                }
            ],
        }
    ]
}


@pytest.mark.asyncio
@patch("polars_baseball.apis.mlb.stats.default_context")
async def test_mlb_pitch_arsenal_basic(mock_default_ctx: MagicMock) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=json.dumps(_MOCK_PITCH_ARSENAL_JSON))
    mock_default_ctx.return_value = BaseballContext(http=mock_http)

    df = await mlb_pitch_arsenal(person_id=545361, season=2024)
    assert isinstance(df, pl.DataFrame)
    assert df.height == 1
    assert df["personId"][0] == 545361
    assert df["season"][0] == 2024
    assert df["pitchTypeCode"][0] == "FF"
    assert df["pitchTypeName"][0] == "Four-Seam Fastball"
    assert df["percentage"][0] == 50.5
    assert df["averageSpeed"][0] == 95.2


@pytest.mark.asyncio
async def test_mlb_pitch_arsenal_invalid_params() -> None:
    with pytest.raises(InvalidParameterError, match="person_id must be a positive integer"):
        await mlb_pitch_arsenal(person_id=0, season=2024)
    with pytest.raises(InvalidParameterError, match="Invalid season"):
        await mlb_pitch_arsenal(person_id=545361, season=1800)


_MOCK_TRANSACTIONS_JSON = {
    "transactions": [
        {
            "id": 12345,
            "date": "2024-05-01",
            "description": "Team A optioned Player B to Team C.",
            "typeCode": "OPT",
            "typeDesc": "Optioned",
            "person": {"id": 656941, "fullName": "Player B"},
            "fromTeam": {"id": 110, "name": "Team A"},
            "toTeam": {"id": 111, "name": "Team C"},
        }
    ]
}


@pytest.mark.asyncio
@patch("polars_baseball.apis.mlb.transactions.default_context")
async def test_mlb_transactions_basic(mock_default_ctx: MagicMock) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=json.dumps(_MOCK_TRANSACTIONS_JSON))
    mock_default_ctx.return_value = BaseballContext(http=mock_http)

    df = await mlb_transactions(date="2024-05-01")
    assert isinstance(df, pl.DataFrame)
    assert df.height == 1
    assert df["id"][0] == 12345
    assert df["date"][0] == "2024-05-01"
    assert df["typeCode"][0] == "OPT"
    assert df["playerId"][0] == 656941
    assert df["fromTeamId"][0] == 110
    assert df["toTeamId"][0] == 111


@pytest.mark.asyncio
async def test_mlb_transactions_invalid_params() -> None:
    with pytest.raises(InvalidParameterError, match="Invalid format for parameter date"):
        await mlb_transactions(date="2024/05/01")
    with pytest.raises(InvalidParameterError, match="Invalid format for parameter start_date"):
        await mlb_transactions(start_date="05-01-2024")
    with pytest.raises(InvalidParameterError, match="sport_id must be a positive integer."):
        await mlb_transactions(sport_id=0)


_MOCK_VENUES_JSON = {
    "venues": [
        {
            "id": 10,
            "name": "Dodger Stadium",
            "link": "/api/v1/venues/10",
            "active": True,
            "season": "2024",
        }
    ]
}


@pytest.mark.asyncio
@patch("polars_baseball.apis.mlb.venues.default_context")
async def test_mlb_venues_basic(mock_default_ctx: MagicMock) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=json.dumps(_MOCK_VENUES_JSON))
    mock_default_ctx.return_value = BaseballContext(http=mock_http)

    # 1. Single ID
    df = await mlb_venues(venue_ids=10)
    assert isinstance(df, pl.DataFrame)
    assert df.height == 1
    assert df["id"][0] == 10
    assert df["name"][0] == "Dodger Stadium"
    assert df["active"][0] is True

    # 2. List of IDs
    df_list = await mlb_venues(venue_ids=[10, 20])
    assert df_list.height == 1


@pytest.mark.asyncio
async def test_mlb_venues_invalid_params() -> None:
    with pytest.raises(InvalidParameterError, match="venue_ids must be a positive integer"):
        await mlb_venues(venue_ids=0)
    with pytest.raises(InvalidParameterError, match="All venue IDs in list must be positive integers"):
        await mlb_venues(venue_ids=[10, -5])


_MOCK_LIVE_FEED_JSON = {
    "liveData": {
        "plays": {
            "allPlays": [
                {
                    "about": {
                        "atBatIndex": 0,
                        "event": "Strikeout",
                        "description": "Strikeout",
                        "playId": "play-1",
                    },
                    "matchup": {
                        "batter": {"id": 545361, "fullName": "Mike Trout"},
                        "pitcher": {"id": 675911, "fullName": "Spencer Strider"},
                    },
                    "playEvents": [
                        {
                            "isPitch": True,
                            "index": 0,
                            "pitchNumber": 1,
                            "details": {
                                "event": "Ball",
                                "description": "Ball",
                                "type": {"code": "FF", "description": "Four-Seam Fastball"},
                            },
                            "pitchData": {
                                "startSpeed": 98.4,
                                "breaks": {"spinRate": 2450},
                            },
                        }
                    ],
                }
            ]
        }
    }
}


@pytest.mark.asyncio
@patch("polars_baseball.apis.mlb.game.default_context")
async def test_mlb_game_feed_live_basic(mock_default_ctx: MagicMock) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=json.dumps(_MOCK_LIVE_FEED_JSON))
    mock_default_ctx.return_value = BaseballContext(http=mock_http)

    df = await mlb_game_feed_live(game_pk=715789)
    assert isinstance(df, pl.DataFrame)
    assert df.height == 1
    assert df["gamePk"][0] == 715789
    assert df["atBatIndex"][0] == 0
    assert df["pitchIndex"][0] == 0
    assert df["pitchNumber"][0] == 1
    assert df["playId"][0] == "play-1"
    assert df["batterName"][0] == "Mike Trout"
    assert df["pitcherName"][0] == "Spencer Strider"
    assert df["pitchType"][0] == "FF"
    assert df["releaseSpeed"][0] == 98.4
    assert df["spinRate"][0] == 2450


@pytest.mark.asyncio
async def test_mlb_game_feed_live_invalid_params() -> None:
    with pytest.raises(InvalidParameterError, match="game_pk must be a positive integer"):
        await mlb_game_feed_live(game_pk=0)


@pytest.mark.asyncio
@patch("polars_baseball.apis.mlb.draft.default_context")
async def test_mlb_draft_fail_fast(mock_default_ctx: MagicMock) -> None:
    bad_json = {
        "drafts": {
            "rounds": [
                {
                    "round": "1",
                    "picks": [
                        {
                            "pickNumber": 1,
                            "person": {"id": 660271},
                        }
                    ],
                }
            ]
        }
    }
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=json.dumps(bad_json))
    mock_default_ctx.return_value = BaseballContext(http=mock_http)

    with pytest.raises(UpstreamParseError):
        await mlb_draft(year=2019)


@pytest.mark.asyncio
@patch("polars_baseball.apis.mlb.stats.default_context")
async def test_mlb_pitch_arsenal_fail_fast(mock_default_ctx: MagicMock) -> None:
    bad_json = {
        "stats": [
            {
                "type": {"displayName": "pitchArsenal"},
                "splits": [{"stat": {"percentage": 50.5}}],
            }
        ]
    }
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=json.dumps(bad_json))
    mock_default_ctx.return_value = BaseballContext(http=mock_http)

    with pytest.raises(UpstreamParseError):
        await mlb_pitch_arsenal(person_id=545361, season=2024)


@pytest.mark.asyncio
@patch("polars_baseball.apis.mlb.transactions.default_context")
async def test_mlb_transactions_fail_fast(mock_default_ctx: MagicMock) -> None:
    bad_json = {
        "transactions": [
            {
                "id": 12345,
                "typeCode": "OPT",
                "typeDesc": "Optioned",
            }
        ]
    }
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=json.dumps(bad_json))
    mock_default_ctx.return_value = BaseballContext(http=mock_http)

    with pytest.raises(UpstreamParseError):
        await mlb_transactions(date="2024-05-01")


_MOCK_LINESCORE_JSON = {
    "innings": [
        {
            "num": 1,
            "home": {"runs": 0, "hits": 1, "errors": 0},
            "away": {"runs": 1, "hits": 2, "errors": 0},
        },
        {
            "num": 2,
            "home": {"runs": 2, "hits": 3, "errors": 1},
            "away": {"runs": 0, "hits": 0, "errors": 0},
        },
    ]
}


@pytest.mark.asyncio
@patch("polars_baseball.apis.mlb.game.default_context")
async def test_mlb_game_linescore_basic(mock_default_ctx: MagicMock) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=json.dumps(_MOCK_LINESCORE_JSON))
    mock_default_ctx.return_value = BaseballContext(http=mock_http)

    df = await mlb_game_linescore(game_pk=715789)
    assert isinstance(df, pl.DataFrame)
    assert df.height == 2
    assert df["gamePk"][0] == 715789
    assert df["inning"][0] == 1
    assert df["homeRuns"][0] == 0
    assert df["homeHits"][0] == 1
    assert df["homeErrors"][0] == 0
    assert df["awayRuns"][0] == 1
    assert df["awayHits"][0] == 2
    assert df["awayErrors"][0] == 0

    assert df["inning"][1] == 2
    assert df["homeRuns"][1] == 2
    assert df["homeHits"][1] == 3
    assert df["homeErrors"][1] == 1
    assert df["awayRuns"][1] == 0
    assert df["awayHits"][1] == 0
    assert df["awayErrors"][1] == 0


@pytest.mark.asyncio
async def test_mlb_game_linescore_invalid_params() -> None:
    with pytest.raises(InvalidParameterError, match="game_pk must be a positive integer"):
        await mlb_game_linescore(game_pk=0)


@pytest.mark.asyncio
@patch("polars_baseball.apis.mlb.game.default_context")
async def test_mlb_game_linescore_empty(mock_default_ctx: MagicMock) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=json.dumps({}))
    mock_default_ctx.return_value = BaseballContext(http=mock_http)

    df = await mlb_game_linescore(game_pk=715789)
    assert isinstance(df, pl.DataFrame)
    assert df.height == 0


@pytest.mark.asyncio
@patch("polars_baseball.apis.mlb.game.default_context")
async def test_mlb_game_linescore_caching_and_force_update(mock_default_ctx: MagicMock) -> None:
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=json.dumps(_MOCK_LINESCORE_JSON))
    mock_default_ctx.return_value = BaseballContext(http=mock_http)

    # 1. First fetch (cache miss)
    df1 = await mlb_game_linescore(game_pk=715789)
    assert df1.height == 2
    assert mock_http.get_text.call_count == 1

    # 2. Second fetch within TTL (cache hit)
    df2 = await mlb_game_linescore(game_pk=715789)
    assert df2.height == 2
    assert mock_http.get_text.call_count == 1

    # 3. Third fetch with force_update=True (bypasses cache)
    df3 = await mlb_game_linescore(game_pk=715789, force_update=True)
    assert df3.height == 2
    assert mock_http.get_text.call_count == 2


@pytest.mark.asyncio
async def test_mlb_game_linescore_accepts_custom_cache_max_age() -> None:
    mock_cache = MagicMock()
    mock_cache.get.return_value = None
    mock_cache.set.return_value = None
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=json.dumps(_MOCK_LINESCORE_JSON))
    ctx = BaseballContext(http=mock_http, cache=mock_cache)
    cache_max_age = timedelta(minutes=5)

    df = await mlb_game_linescore(game_pk=715789, cache_max_age=cache_max_age, context=ctx)

    assert df.height == 2
    mock_cache.get.assert_called_once()
    assert mock_cache.get.call_args.kwargs["max_age"] == cache_max_age


@pytest.mark.asyncio
@patch("polars_baseball.apis.mlb.game.default_context")
async def test_mlb_game_linescore_bad_home_away(mock_default_ctx: MagicMock) -> None:
    bad_json = {
        "innings": [
            {
                "num": 1,
                "home": None,
                "away": "not_a_dict",
            }
        ]
    }
    mock_http = AsyncMock(spec=HttpClient)
    mock_http.get_text = AsyncMock(return_value=json.dumps(bad_json))
    mock_default_ctx.return_value = BaseballContext(http=mock_http)

    df = await mlb_game_linescore(game_pk=715789)
    assert isinstance(df, pl.DataFrame)
    assert df.height == 1
    assert df["homeRuns"][0] is None
    assert df["awayRuns"][0] is None
