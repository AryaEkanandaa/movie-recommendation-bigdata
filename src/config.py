import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parents[1]

DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw" / "tmdb"

DISCOVER_BATCH_DIR = RAW_DIR / "discover_batches"
ENRICH_BATCH_DIR = RAW_DIR / "enrich_batches"
FAILURE_DIR = RAW_DIR / "failures"
LOG_DIR = BASE_DIR / "logs"

for path in [
    RAW_DIR,
    DISCOVER_BATCH_DIR,
    ENRICH_BATCH_DIR,
    FAILURE_DIR,
    LOG_DIR,
]:
    path.mkdir(parents=True, exist_ok=True)

TMDB_BEARER_TOKEN = os.getenv("TMDB_BEARER_TOKEN")

TARGET_ROWS = int(os.getenv("TARGET_ROWS", "50000"))
START_YEAR = int(os.getenv("START_YEAR", "1900"))
END_YEAR = int(os.getenv("END_YEAR", "2026"))

MIN_VOTE_COUNT_FIRST = int(os.getenv("MIN_VOTE_COUNT_FIRST", "10"))
MIN_VOTE_COUNT_SECOND = int(os.getenv("MIN_VOTE_COUNT_SECOND", "0"))

REQUEST_SLEEP_SECONDS = float(os.getenv("REQUEST_SLEEP_SECONDS", "0.25"))

BASE_MOVIES_OUTPUT = RAW_DIR / f"tmdb_movies_base_{TARGET_ROWS}.csv"
FAILURES_OUTPUT = FAILURE_DIR / "discover_failures.csv"