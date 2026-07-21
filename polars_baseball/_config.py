import os
from pathlib import Path

DEFAULT_CACHE_DIR = Path(os.getenv("POLARS_BASEBALL_CACHE_DIR", str(Path.home() / ".polars_baseball" / "cache")))
COMPILED_DATASETS_ROOT_URL = os.getenv("POLARS_BASEBALL_DATASETS_URL", "").rstrip("/")

if COMPILED_DATASETS_ROOT_URL and not COMPILED_DATASETS_ROOT_URL.startswith(("http://", "https://")):
    raise ValueError(
        f"POLARS_BASEBALL_DATASETS_URL must start with http:// or https://, got: {COMPILED_DATASETS_ROOT_URL!r}"
    )

SAVANT_ROOT = "https://baseballsavant.mlb.com"
BREF_ROOT = "https://www.baseball-reference.com"
FG_ROOT = "https://www.fangraphs.com"
MLB_ROOT = "https://www.mlb.com"
STATS_API_ROOT = "https://statsapi.mlb.com/api/v1"
MILB_ROOT = f"{MLB_ROOT}/milb"
RETROSHEET_ROOT = "https://raw.githubusercontent.com/chadwickbureau/retrosheet"
GITHUB_ROOT = "https://github.com"
GITHUB_API_ROOT = "https://api.github.com"
CHADWICK_ORG = "chadwickbureau"

SAVANT_STATCAST_SEARCH_URL = f"{SAVANT_ROOT}/statcast_search/csv"
SAVANT_GAMEFEED_URL = f"{SAVANT_ROOT}/gf"
FG_LEADERS_URL = f"{FG_ROOT}/leaders.aspx"
RETROSHEET_GAMELOG_URL = f"{RETROSHEET_ROOT}/master/gamelog/GL{{}}.TXT"
RETROSHEET_SEASON_GAMELOG_URL = f"{RETROSHEET_ROOT}/master/seasons/{{}}/GL{{}}.TXT"
RETROSHEET_SCHEDULE_URL = f"{RETROSHEET_ROOT}/master/seasons/{{}}/{{}}schedule.csv"
RETROSHEET_PARKID_URL = f"{RETROSHEET_ROOT}/master/reference/ballparks.csv"
RETROSHEET_ROSTER_URL = f"{RETROSHEET_ROOT}/master/seasons/{{}}/{{}}{{}}.ROS"
RETROSHEET_EVENT_URL = f"{RETROSHEET_ROOT}/master/seasons/{{}}/{{}}"

DEFAULT_TIMEOUT = 30.0
DEFAULT_MAX_RETRIES = 2
DEFAULT_STATCAST_CONCURRENCY_LIMIT = 3

STATCAST_FIRST_YEAR: int = 2008
PROSPECT_RANKINGS_START_YEAR: int = 2011

SEASON_MID_MARCH_DAY: int = 15

MLB_FIRST_YEAR: int = 1876

DEFAULT_CSV_INFER_SCHEMA_LENGTH: int = 10_000

SAVANT_INVALID_PLAYER_ID: int = 999_999

OVERSIZE_DAYS_THRESHOLD: int = 42

STATCAST_DATE_STEP: int = 7

FUZZY_MIN_SIZE_FOR_FILTER: int = 1000
FUZZY_NAME_LENGTH_TOLERANCE: int = 3
FUZZY_FALLBACK_MIN_RESULTS: int = 5
FUZZY_MATCH_LIMIT: int = 5
FUZZY_MATCH_CUTOFF: int = 0

FG_MAX_RESULTS: int = 1_000_000

LAHMAN_ARCHIVE_URL = f"{GITHUB_ROOT}/cbwinslow/baseballdatabank/archive/refs/heads/master.zip"
CHADWICK_REGISTER_ARCHIVE_URL = f"{GITHUB_ROOT}/{CHADWICK_ORG}/register/archive/refs/heads/master.zip"
RETROSHEET_CONTENTS_URL_TEMPLATE = f"{GITHUB_API_ROOT}/repos/{CHADWICK_ORG}/retrosheet/contents/seasons/{{}}"
