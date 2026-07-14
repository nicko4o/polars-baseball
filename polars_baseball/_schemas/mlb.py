from typing import Final

import polars as pl

MLB_PEOPLE_REQUIRED: Final[tuple[str, ...]] = ("id", "fullName")
MLB_PEOPLE_TYPES: Final[dict[str, pl.DataType | type[pl.DataType]]] = {
    "id": pl.Int64,
    "fullName": pl.String,
    "firstName": pl.String,
    "lastName": pl.String,
    "primaryNumber": pl.String,
    "birthDate": pl.String,
    "currentAge": pl.Int64,
    "birthCity": pl.String,
    "birthStateProvince": pl.String,
    "birthCountry": pl.String,
    "height": pl.String,
    "weight": pl.Int64,
    "active": pl.Boolean,
    "primaryPositionCode": pl.String,
    "primaryPositionName": pl.String,
    "primaryPositionAbbrev": pl.String,
    "useName": pl.String,
    "boxscoreName": pl.String,
    "gender": pl.String,
    "isPlayer": pl.Boolean,
    "isVerified": pl.Boolean,
    "draftYear": pl.Int64,
    "mlbDebutDate": pl.String,
    "batSideCode": pl.String,
    "pitchHandCode": pl.String,
}

MLB_SCHEDULE_REQUIRED: Final[tuple[str, ...]] = ("gamePk", "season", "gameDate")
MLB_SCHEDULE_TYPES: Final[dict[str, pl.DataType | type[pl.DataType]]] = {
    "gamePk": pl.Int64,
    "gameType": pl.String,
    "season": pl.String,
    "gameDate": pl.String,
    "officialDate": pl.String,
    "statusAbstract": pl.String,
    "statusCode": pl.String,
    "statusDetailed": pl.String,
    "awayTeamId": pl.Int64,
    "awayTeamName": pl.String,
    "awayScore": pl.Int64,
    "awayProbablePitcherId": pl.Int64,
    "awayProbablePitcherName": pl.String,
    "homeTeamId": pl.Int64,
    "homeTeamName": pl.String,
    "homeScore": pl.Int64,
    "homeProbablePitcherId": pl.Int64,
    "homeProbablePitcherName": pl.String,
    "venueId": pl.Int64,
    "venueName": pl.String,
    "doubleHeader": pl.String,
    "gamedayType": pl.String,
    "tiebreaker": pl.String,
    "calendarEventID": pl.String,
    "seasonDisplay": pl.String,
    "dayNight": pl.String,
    "description": pl.String,
    "scheduledInnings": pl.Int64,
    "gamesInSeries": pl.Int64,
    "seriesGameNumber": pl.Int64,
    "seriesDescription": pl.String,
    "awayHits": pl.Int64,
    "awayErrors": pl.Int64,
    "homeHits": pl.Int64,
    "homeErrors": pl.Int64,
    "winnerPitcherId": pl.Int64,
    "winnerPitcherName": pl.String,
    "loserPitcherId": pl.Int64,
    "loserPitcherName": pl.String,
    "savePitcherId": pl.Int64,
    "savePitcherName": pl.String,
}

MLB_ROSTER_REQUIRED: Final[tuple[str, ...]] = ("teamId", "personId", "fullName")
MLB_ROSTER_TYPES: Final[dict[str, pl.DataType | type[pl.DataType]]] = {
    "teamId": pl.Int64,
    "personId": pl.Int64,
    "fullName": pl.String,
    "jerseyNumber": pl.String,
    "positionCode": pl.String,
    "positionName": pl.String,
    "positionAbbrev": pl.String,
    "positionType": pl.String,
    "statusCode": pl.String,
    "statusDesc": pl.String,
}

MLB_PLAYER_STATS_REQUIRED: Final[tuple[str, ...]] = ("personId", "group", "statType")
MLB_PLAYER_STATS_TYPES: Final[dict[str, pl.DataType | type[pl.DataType]]] = {
    "personId": pl.Int64,
    "season": pl.Int64,
    "group": pl.String,
    "statType": pl.String,
}

MLB_BOXSCORE_REQUIRED: Final[tuple[str, ...]] = ("gamePk", "teamId", "personId", "fullName")
MLB_BOXSCORE_TYPES: Final[dict[str, pl.DataType | type[pl.DataType]]] = {
    "gamePk": pl.Int64,
    "teamId": pl.Int64,
    "personId": pl.Int64,
    "fullName": pl.String,
    "jerseyNumber": pl.String,
    "positionCode": pl.String,
    "positionName": pl.String,
    "positionAbbrev": pl.String,
}

MLB_BOXSCORE_STATS_TYPES: Final[dict[str, pl.DataType | type[pl.DataType]]] = {
    **MLB_BOXSCORE_TYPES,
    "batting_atBats": pl.Int64,
    "batting_runs": pl.Int64,
    "batting_hits": pl.Int64,
    "batting_doubles": pl.Int64,
    "batting_triples": pl.Int64,
    "batting_homeRuns": pl.Int64,
    "batting_rbi": pl.Int64,
    "batting_baseOnBalls": pl.Int64,
    "batting_strikeOuts": pl.Int64,
    "batting_leftOnBase": pl.Int64,
    "batting_groundIntoDoublePlay": pl.Int64,
    "batting_stolenBases": pl.Int64,
    "batting_caughtStealing": pl.Int64,
    "fielding_errors": pl.Int64,
    "pitching_inningsPitched": pl.String,
    "pitching_hits": pl.Int64,
    "pitching_runs": pl.Int64,
    "pitching_earnedRuns": pl.Int64,
    "pitching_baseOnBalls": pl.Int64,
    "pitching_strikeOuts": pl.Int64,
    "pitching_homeRuns": pl.Int64,
    "pitching_outs": pl.Int64,
    "isInBattingOrder": pl.Boolean,
    "battingOrder": pl.Int64,
}

MLB_TEAM_STATS_REQUIRED: Final[tuple[str, ...]] = ("teamId", "season", "group", "statType")
MLB_TEAM_STATS_TYPES: Final[dict[str, pl.DataType | type[pl.DataType]]] = {
    "teamId": pl.Int64,
    "season": pl.Int64,
    "group": pl.String,
    "statType": pl.String,
}

MLB_TEAMS_REQUIRED: Final[tuple[str, ...]] = ("id", "name", "abbreviation")
MLB_TEAMS_TYPES: Final[dict[str, pl.DataType | type[pl.DataType]]] = {
    "id": pl.Int64,
    "name": pl.String,
    "abbreviation": pl.String,
    "teamName": pl.String,
    "locationName": pl.String,
    "leagueId": pl.Int64,
    "leagueName": pl.String,
    "divisionId": pl.Int64,
    "divisionName": pl.String,
    "venueId": pl.Int64,
    "venueName": pl.String,
    "springLeague": pl.String,
    "season": pl.Int64,
}

MLB_DIVISIONS_REQUIRED: Final[tuple[str, ...]] = ("id", "name")
MLB_DIVISIONS_TYPES: Final[dict[str, pl.DataType | type[pl.DataType]]] = {
    "id": pl.Int64,
    "name": pl.String,
    "nameShort": pl.String,
    "abbreviation": pl.String,
    "season": pl.Int64,
    "leagueId": pl.Int64,
    "sportId": pl.Int64,
    "hasWildcard": pl.Boolean,
    "sortOrder": pl.Int64,
    "numPlayoffTeams": pl.Int64,
    "active": pl.Boolean,
}

MLB_LEAGUES_REQUIRED: Final[tuple[str, ...]] = ("id", "name")
MLB_LEAGUES_TYPES: Final[dict[str, pl.DataType | type[pl.DataType]]] = {
    "id": pl.Int64,
    "name": pl.String,
    "nameShort": pl.String,
    "abbreviation": pl.String,
    "orgCode": pl.String,
    "season": pl.Int64,
    "seasonState": pl.String,
    "active": pl.Boolean,
    "sportId": pl.Int64,
    "numTeams": pl.Int64,
    "numGames": pl.Int64,
    "numWildcardTeams": pl.Int64,
    "hasWildCard": pl.Boolean,
    "divisionsInUse": pl.Boolean,
    "sortOrder": pl.Int64,
}

MLB_PEOPLE_AWARDS_REQUIRED: Final[tuple[str, ...]] = ("personId", "awardId", "awardName")
MLB_PEOPLE_AWARDS_TYPES: Final[dict[str, pl.DataType | type[pl.DataType]]] = {
    "personId": pl.Int64,
    "awardId": pl.String,
    "awardName": pl.String,
    "date": pl.String,
    "season": pl.Int64,
    "teamId": pl.Int64,
    "teamName": pl.String,
    "positionCode": pl.String,
    "positionName": pl.String,
    "positionType": pl.String,
    "positionAbbreviation": pl.String,
}

MLB_PBP_REQUIRED: Final[tuple[str, ...]] = ("gamePk", "atBatIndex", "inning")
MLB_PBP_TYPES: Final[dict[str, pl.DataType | type[pl.DataType]]] = {
    "gamePk": pl.Int64,
    "atBatIndex": pl.Int64,
    "inning": pl.Int64,
    "halfInning": pl.String,
    "batterId": pl.Int64,
    "batterName": pl.String,
    "pitcherId": pl.Int64,
    "pitcherName": pl.String,
    "description": pl.String,
    "event": pl.String,
    "eventType": pl.String,
    "balls": pl.Int64,
    "strikes": pl.Int64,
    "outs": pl.Int64,
    "homeScore": pl.Int64,
    "awayScore": pl.Int64,
    "rbi": pl.Int64,
    "homeTeamWinProbability": pl.Float64,
    "awayTeamWinProbability": pl.Float64,
    "homeTeamWinProbabilityAdded": pl.Float64,
    "leverageIndex": pl.Float64,
    "dramaIndex": pl.Float64,
}

MLB_STAT_LEADERS_REQUIRED: Final[tuple[str, ...]] = ("personId", "category", "rank")
MLB_STAT_LEADERS_TYPES: Final[dict[str, pl.DataType | type[pl.DataType]]] = {
    "rank": pl.Int64,
    "personId": pl.Int64,
    "personName": pl.String,
    "teamId": pl.Int64,
    "teamName": pl.String,
    "leagueId": pl.Int64,
    "category": pl.String,
    "value": pl.Float64,
    "season": pl.Int64,
    "statGroup": pl.String,
}

MLB_DRAFT_REQUIRED: Final[tuple[str, ...]] = ("year", "round", "pickNumber", "playerName")
MLB_DRAFT_TYPES: Final[dict[str, pl.DataType | type[pl.DataType]]] = {
    "year": pl.Int64,
    "round": pl.String,
    "pickNumber": pl.Int64,
    "roundPickNumber": pl.Int64,
    "playerName": pl.String,
    "playerId": pl.Int64,
    "teamId": pl.Int64,
    "teamName": pl.String,
    "signingBonus": pl.Int64,
    "homeSchool": pl.String,
}

MLB_PITCH_ARSENAL_REQUIRED: Final[tuple[str, ...]] = ("personId", "season", "pitchTypeCode", "pitchTypeName")
MLB_PITCH_ARSENAL_TYPES: Final[dict[str, pl.DataType | type[pl.DataType]]] = {
    "personId": pl.Int64,
    "season": pl.Int64,
    "pitchTypeCode": pl.String,
    "pitchTypeName": pl.String,
    "percentage": pl.Float64,
    "averageSpeed": pl.Float64,
}

MLB_TRANSACTIONS_REQUIRED: Final[tuple[str, ...]] = ("id", "date", "description", "typeCode", "typeDesc")
MLB_TRANSACTIONS_TYPES: Final[dict[str, pl.DataType | type[pl.DataType]]] = {
    "id": pl.Int64,
    "date": pl.String,
    "description": pl.String,
    "typeCode": pl.String,
    "typeDesc": pl.String,
    "playerId": pl.Int64,
    "playerName": pl.String,
    "fromTeamId": pl.Int64,
    "fromTeamName": pl.String,
    "toTeamId": pl.Int64,
    "toTeamName": pl.String,
}

MLB_VENUES_REQUIRED: Final[tuple[str, ...]] = ("id", "name")
MLB_VENUES_TYPES: Final[dict[str, pl.DataType | type[pl.DataType]]] = {
    "id": pl.Int64,
    "name": pl.String,
    "link": pl.String,
    "active": pl.Boolean,
    "season": pl.String,
}

MLB_LIVE_FEED_REQUIRED: Final[tuple[str, ...]] = ("gamePk", "atBatIndex", "pitchIndex")
MLB_LIVE_FEED_TYPES: Final[dict[str, pl.DataType | type[pl.DataType]]] = {
    "gamePk": pl.Int64,
    "atBatIndex": pl.Int64,
    "pitchIndex": pl.Int64,
    "pitchNumber": pl.Int64,
    "playId": pl.String,
    "batterId": pl.Int64,
    "batterName": pl.String,
    "pitcherId": pl.Int64,
    "pitcherName": pl.String,
    "event": pl.String,
    "description": pl.String,
    "pitchType": pl.String,
    "releaseSpeed": pl.Float64,
    "spinRate": pl.Int64,
}

MLB_LINESCORE_REQUIRED: Final[tuple[str, ...]] = ("gamePk", "inning")
MLB_LINESCORE_TYPES: Final[dict[str, pl.DataType | type[pl.DataType]]] = {
    "gamePk": pl.Int64,
    "inning": pl.Int64,
    "homeRuns": pl.Int64,
    "homeHits": pl.Int64,
    "homeErrors": pl.Int64,
    "awayRuns": pl.Int64,
    "awayHits": pl.Int64,
    "awayErrors": pl.Int64,
}
