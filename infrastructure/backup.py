"""
backup.py — automated PostgreSQL backups with rotation.
"""

import argparse
import logging
import os
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import BACKUP_DIR, BACKUP_RETENTION_DAYS, DATABASE_URL

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)

CONTAINER_NAME = "kasipitchside_postgres"


def _get_db_credentials() -> tuple[str, str]:
    """Extract postgres user and db name from DATABASE_URL or environment."""
    parsed = urlparse(DATABASE_URL)
    user = parsed.username or os.getenv("POSTGRES_USER", "postgres")
    db_name = parsed.path.lstrip("/") or os.getenv("POSTGRES_DB", "kasipitchside")
    return user, db_name


def take_backup() -> Path:
    """Run pg_dump inside the Postgres container, write output to BACKUP_DIR."""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)

    user, db_name = _get_db_credentials()
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = BACKUP_DIR / f"psl_warehouse_{timestamp}.sql"

    logger.info(f"Starting backup -> {backup_file}")

    cmd = [
        "docker", "exec", CONTAINER_NAME,
        "pg_dump",
        "-U", user,
        "-d", db_name,
        "-Fp",
    ]

    try:
        with open(backup_file, "w", encoding="utf-8") as f:
            result = subprocess.run(
                cmd, stdout=f, stderr=subprocess.PIPE, text=True, timeout=300
            )
    except subprocess.TimeoutExpired:
        logger.error("Backup timed out after 300s")
        backup_file.unlink(missing_ok=True)
        raise

    if result.returncode != 0:
        logger.error(f"pg_dump failed: {result.stderr}")
        backup_file.unlink(missing_ok=True)
        raise RuntimeError(f"pg_dump exited with code {result.returncode}: {result.stderr}")

    size_kb = backup_file.stat().st_size / 1024
    if size_kb == 0:
        logger.error("Backup file is empty — treating as a failed backup")
        backup_file.unlink(missing_ok=True)
        raise RuntimeError("pg_dump produced an empty file")

    logger.info(f"Backup complete: {backup_file.name} ({size_kb:.1f} KB)")
    return backup_file


def rotate_backups() -> int:
    """Delete backups older than BACKUP_RETENTION_DAYS. Returns count deleted."""
    if not BACKUP_DIR.exists():
        return 0

    cutoff = datetime.now().timestamp() - (BACKUP_RETENTION_DAYS * 86400)
    deleted = 0

    for backup_file in BACKUP_DIR.glob("psl_warehouse_*.sql"):
        if backup_file.stat().st_mtime < cutoff:
            logger.info(f"Rotating out old backup: {backup_file.name}")
            backup_file.unlink()
            deleted += 1

    if deleted:
        logger.info(f"Rotation complete: removed {deleted} backup(s) older than {BACKUP_RETENTION_DAYS} days")
    else:
        logger.info("Rotation complete: nothing to remove")

    return deleted


def main() -> None:
    parser = argparse.ArgumentParser(description="Back up the Kasi Pitchside database.")
    parser.add_argument("--no-rotate", action="store_true", help="Skip rotation after backup")
    args = parser.parse_args()

    take_backup()

    if not args.no_rotate:
        rotate_backups()


if __name__ == "__main__":
    main()