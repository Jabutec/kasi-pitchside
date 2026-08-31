import os
from pathlib import Path

from dotenv import load_dotenv

# Load .env before anything else
_env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=_env_path)


# Paths
PROJECT_ROOT = Path(__file__).parent.parent.resolve()

RAW_DIR = PROJECT_ROOT / "raw"
LOG_DIR = PROJECT_ROOT / "logs"
OUTPUT_DIR = PROJECT_ROOT / "output"
BACKUP_DIR = PROJECT_ROOT / "backups"
LOOKUPS_DIR = PROJECT_ROOT / "lookups"
WAREHOUSE_DIR = PROJECT_ROOT / "warehouse"

SQLITE_PATH = WAREHOUSE_DIR / "local_dev.db"


def init_directories() -> None:
    """Create runtime directories. Call once at startup — never at import time."""
    for d in (RAW_DIR, LOG_DIR, OUTPUT_DIR, BACKUP_DIR, LOOKUPS_DIR, WAREHOUSE_DIR):
        d.mkdir(parents=True, exist_ok=True)


# Database
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://changeme_user:changeme_password@localhost:5432/psl_warehouse",
)


# Connection Pooling
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "5"))
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "10"))
DB_POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "3600"))
# ADDED: was hardcoded directly in db.py (pool_timeout=30), breaking the
# pattern used by every other pool setting here. Now configurable like
# the rest, with the same default.
DB_POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))


# Source orchestration
SOURCE_PRIORITY = ["livescore", "flashscore", "psl_website", "google_search"]

SOURCE_RATE_LIMITS = {
    "livescore": 2.5,
    "flashscore": 2.5,
    "psl_website": 3.0,
    "google_search": 5.0,
}


# Pipeline scheduling
FIXTURES_LOOKAHEAD_DAYS = 7
LIVE_SCORE_POLL_INTERVAL = 180
POST_MATCH_DELAY_HOURS = 2
RECONCILE_DELAY_HOURS = 24


# Data retention
RAW_CACHE_RETENTION_DAYS = int(os.getenv("RAW_CACHE_RETENTION_DAYS", "30"))
LOG_RETENTION_DAYS = int(os.getenv("LOG_RETENTION_DAYS", "90"))
BACKUP_RETENTION_DAYS = int(os.getenv("BACKUP_RETENTION_DAYS", "30"))


# Graphics
CANVAS_SIZES = {
    "square": (1080, 1080),
    "portrait": (1080, 1350),
    "story": (1080, 1920),
}