from typing import TypedDict


class PersonDict(TypedDict, total=False):
    id: int | None
    fullName: str | None
    firstName: str | None
    lastName: str | None
    primaryNumber: str | None
    birthDate: str | None
    currentAge: int | None
    birthCity: str | None
    birthStateProvince: str | None
    birthCountry: str | None
    height: str | None
    weight: int | None
    active: bool | None
    primaryPositionCode: str | None
    primaryPositionName: str | None
    primaryPositionAbbrev: str | None
    useName: str | None
    boxscoreName: str | None
    gender: str | None
    isPlayer: bool | None
    isVerified: bool | None
    draftYear: int | None
    mlbDebutDate: str | None
    batSideCode: str | None
    pitchHandCode: str | None


class GameDict(TypedDict, total=False):
    gamePk: int | None
    gameType: str | None
    season: str | None
    gameDate: str | None
    officialDate: str | None
    statusAbstract: str | None
    statusCode: str | None
    statusDetailed: str | None
    awayTeamId: int | None
    awayTeamName: str | None
    awayScore: int | None
    awayProbablePitcherId: int | None
    awayProbablePitcherName: str | None
    homeTeamId: int | None
    homeTeamName: str | None
    homeScore: int | None
    homeProbablePitcherId: int | None
    homeProbablePitcherName: str | None
    venueId: int | None
    venueName: str | None
    doubleHeader: bool | None
    gamedayType: str | None
    tiebreaker: bool | None
    calendarEventID: str | None
    seasonDisplay: str | None
    dayNight: str | None
    description: str | None
    scheduledInnings: int | None
    gamesInSeries: int | None
    seriesGameNumber: int | None
    seriesDescription: str | None
    awayHits: int | None
    awayErrors: int | None
    homeHits: int | None
    homeErrors: int | None
    winnerPitcherId: int | None
    winnerPitcherName: str | None
    loserPitcherId: int | None
    loserPitcherName: str | None
    savePitcherId: int | None
    savePitcherName: str | None


class RosterMemberDict(TypedDict, total=False):
    teamId: int | None
    personId: int | None
    fullName: str | None
    jerseyNumber: str | None
    positionCode: str | None
    positionName: str | None
    positionAbbrev: str | None
    isInBattingOrder: bool | None
    battingOrder: int | None
    batting_atBats: int | None
    batting_runs: int | None
    batting_hits: int | None
    batting_doubles: int | None
    batting_triples: int | None
    batting_homeRuns: int | None
    batting_rbi: int | None
    batting_baseOnBalls: int | None
    batting_strikeOuts: int | None
    batting_leftOnBase: int | None
    batting_groundIntoDoublePlay: int | None
    batting_stolenBases: int | None
    batting_caughtStealing: int | None
    fielding_errors: int | None
    pitching_inningsPitched: str | None
    pitching_hits: int | None
    pitching_runs: int | None
    pitching_earnedRuns: int | None
    pitching_baseOnBalls: int | None
    pitching_strikeOuts: int | None
    pitching_homeRuns: int | None
    pitching_outs: int | None
    positionType: str | None
    statusCode: str | None
    statusDesc: str | None


class BoxscorePlayerDict(TypedDict, total=False):
    gamePk: int | None
    teamId: int | None
    personId: int | None
    fullName: str | None
    jerseyNumber: str | None
    positionCode: str | None
    positionName: str | None
    positionAbbrev: str | None


class TeamStatsDict(TypedDict, total=False):
    teamId: int | None
    season: int | None
    group: str | None
    statType: str | None


class TeamDict(TypedDict, total=False):
    id: int | None
    name: str | None
    abbreviation: str | None
    teamName: str | None
    locationName: str | None
    leagueId: int | None
    leagueName: str | None
    divisionId: int | None
    divisionName: str | None
    venueId: int | None
    venueName: str | None
    springLeague: str | None
    season: int | None


class DivisionDict(TypedDict, total=False):
    id: int | None
    name: str | None
    nameShort: str | None
    abbreviation: str | None
    season: int | str | None
    leagueId: int | None
    sportId: int | None
    hasWildcard: bool | None
    sortOrder: int | None
    numPlayoffTeams: int | None
    active: bool | None


class LeagueDict(TypedDict, total=False):
    id: int | None
    name: str | None
    nameShort: str | None
    abbreviation: str | None
    orgCode: str | None
    season: int | str | None
    seasonState: str | None
    active: bool | None
    sportId: int | None
    numTeams: int | None
    numGames: int | None
    numWildcardTeams: int | None
    hasWildCard: bool | None
    divisionsInUse: bool | None
    sortOrder: int | None


class PeopleAwardDict(TypedDict, total=False):
    personId: int | None
    awardId: str | None
    awardName: str | None
    date: str | None
    season: int | str | None
    teamId: int | None
    teamName: str | None
    positionCode: str | None
    positionName: str | None
    positionType: str | None
    positionAbbreviation: str | None


class PlayByPlayDict(TypedDict, total=False):
    gamePk: int | None
    atBatIndex: int | None
    inning: int | None
    halfInning: str | None
    batterId: int | None
    batterName: str | None
    pitcherId: int | None
    pitcherName: str | None
    description: str | None
    event: str | None
    eventType: str | None
    balls: int | None
    strikes: int | None
    outs: int | None
    homeScore: int | None
    awayScore: int | None
    rbi: int | None
    homeTeamWinProbability: float | None
    awayTeamWinProbability: float | None
    homeTeamWinProbabilityAdded: float | None
    leverageIndex: float | None
    dramaIndex: float | None


class StatLeaderDict(TypedDict, total=False):
    rank: int | None
    personId: int | None
    personName: str | None
    teamId: int | None
    teamName: str | None
    leagueId: int | None
    category: str | None
    value: float | None
    season: int | None
    statGroup: str | None


class DraftPickDict(TypedDict, total=False):
    year: int | None
    round: str | None
    pickNumber: int | None
    roundPickNumber: int | None
    playerName: str | None
    playerId: int | None
    teamId: int | None
    teamName: str | None
    signingBonus: int | None
    homeSchool: str | None


class PitchArsenalDict(TypedDict, total=False):
    personId: int | None
    season: int | None
    pitchTypeCode: str | None
    pitchTypeName: str | None
    percentage: float | None
    averageSpeed: float | None


class TransactionDict(TypedDict, total=False):
    id: int | None
    date: str | None
    description: str | None
    typeCode: str | None
    typeDesc: str | None
    playerId: int | None
    playerName: str | None
    fromTeamId: int | None
    fromTeamName: str | None
    toTeamId: int | None
    toTeamName: str | None


class VenueDict(TypedDict, total=False):
    id: int | None
    name: str | None
    link: str | None
    active: bool | None
    season: str | None


class LiveFeedPitchDict(TypedDict, total=False):
    gamePk: int | None
    atBatIndex: int | None
    pitchIndex: int | None
    pitchNumber: int | None
    playId: str | None
    batterId: int | None
    batterName: str | None
    pitcherId: int | None
    pitcherName: str | None
    event: str | None
    description: str | None
    pitchType: str | None
    releaseSpeed: float | None
    spinRate: int | None


class LinescoreDict(TypedDict, total=False):
    gamePk: int | None
    inning: int | None
    homeRuns: int | None
    homeHits: int | None
    homeErrors: int | None
    awayRuns: int | None
    awayHits: int | None
    awayErrors: int | None
