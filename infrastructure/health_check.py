"""
health_check.py — checks disk space, DB connectivity, and backup freshness.
"""

import argparse
import json
import shutil
import sys
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from config.settings import BACKUP_DIR, DATABASE_URL, PROJECT_ROOT

DISK_WARNING_THRESHOLD_PCT = 85  
BACKUP_STALE_HOURS = 30          
                                


@dataclass
class CheckResult:
    name: str
    ok: bool
    detail: str


def check_disk_space() -> CheckResult:
    usage = shutil.disk_usage(PROJECT_ROOT)
    pct_used = (usage.used / usage.total) * 100
    free_gb = usage.free / (1024 ** 3)

    ok = pct_used < DISK_WARNING_THRESHOLD_PCT
    detail = f"{pct_used:.1f}% used, {free_gb:.1f} GB free"
    return CheckResult(name="disk_space", ok=ok, detail=detail)


def check_database_connectivity() -> CheckResult:
    try:
        from sqlalchemy import create_engine, text
        engine = create_engine(DATABASE_URL, pool_pre_ping=True)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        return CheckResult(name="database", ok=True, detail="connected successfully")
    except Exception as e:
        return CheckResult(name="database", ok=False, detail=f"connection failed: {e}")


def check_backup_freshness() -> CheckResult:
    if not BACKUP_DIR.exists():
        return CheckResult(name="backup_freshness", ok=False, detail="backup directory does not exist")

    backups = sorted(BACKUP_DIR.glob("psl_warehouse_*.sql"), key=lambda p: p.stat().st_mtime, reverse=True)

    if not backups:
        return CheckResult(name="backup_freshness", ok=False, detail="no backups found")

    latest = backups[0]
    age_hours = (datetime.now().timestamp() - latest.stat().st_mtime) / 3600

    ok = age_hours < BACKUP_STALE_HOURS
    detail = f"latest backup '{latest.name}' is {age_hours:.1f}h old"
    return CheckResult(name="backup_freshness", ok=ok, detail=detail)


def run_all_checks() -> list[CheckResult]:
    return [
        check_disk_space(),
        check_database_connectivity(),
        check_backup_freshness(),
    ]


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Kasi Pitchside health checks.")
    parser.add_argument("--json", action="store_true", help="Output as JSON")
    args = parser.parse_args()

    results = run_all_checks()
    all_ok = all(r.ok for r in results)

    if args.json:
        print(json.dumps({"healthy": all_ok, "checks": [asdict(r) for r in results]}, indent=2))
    else:
        for r in results:
            status = "OK" if r.ok else "FAIL"
            print(f"[{status}] {r.name}: {r.detail}")
        print(f"\nOverall: {'HEALTHY' if all_ok else 'UNHEALTHY'}")

    sys.exit(0 if all_ok else 1)


if __name__ == "__main__":
    main()