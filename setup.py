"""
setup.py — one-command initialization for Kasi Pitchside.
"""

import subprocess
import sys
import time
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.resolve()
COMPOSE_FILE = PROJECT_ROOT / "infrastructure" / "docker-compose.yml"
ENV_FILE = PROJECT_ROOT / ".env"

HEALTH_CHECK_TIMEOUT_S = 60
HEALTH_CHECK_INTERVAL_S = 3


def step(message: str) -> None:
    print(f"\n==> {message}")


def run(cmd: list[str], **kwargs) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, check=True, **kwargs)


def check_prerequisites() -> None:
    step("Checking prerequisites")

    if not ENV_FILE.exists():
        print(f"ERROR: {ENV_FILE} not found.")
        print("Copy .env.example to .env and fill in real values before running setup.")
        sys.exit(1)

    for tool in ("docker",):
        try:
            subprocess.run([tool, "--version"], capture_output=True, check=True)
        except (subprocess.CalledProcessError, FileNotFoundError):
            print(f"ERROR: '{tool}' not found on PATH. Install it before running setup.")
            sys.exit(1)

    print("  .env found, docker available.")


def create_directories() -> None:
    step("Creating runtime directories")
    from config.settings import init_directories
    init_directories()
    print("  raw/, logs/, output/, backups/, lookups/, warehouse/ ready.")


def start_stack() -> None:
    step("Starting Postgres + PgBouncer via Docker Compose")
    run(
        ["docker", "compose", "-f", str(COMPOSE_FILE), "--env-file", str(ENV_FILE), "up", "-d"],
        cwd=PROJECT_ROOT,
    )


def wait_for_postgres_healthy() -> None:
    step("Waiting for Postgres to report healthy")

    deadline = time.time() + HEALTH_CHECK_TIMEOUT_S
    while time.time() < deadline:
        result = subprocess.run(
            ["docker", "inspect", "--format", "{{.State.Health.Status}}", "kasipitchside_postgres"],
            capture_output=True, text=True,
        )
        status = result.stdout.strip()
        if status == "healthy":
            print("  Postgres is healthy.")
            return
        print(f"  status: {status or 'starting'} — waiting...")
        time.sleep(HEALTH_CHECK_INTERVAL_S)

    print(f"ERROR: Postgres did not become healthy within {HEALTH_CHECK_TIMEOUT_S}s.")
    print("Check logs with: docker logs kasipitchside_postgres")
    sys.exit(1)


def verify_schema() -> None:
    step("Verifying schema is reachable through PgBouncer")
    from infrastructure.health_check import check_database_connectivity

    result = check_database_connectivity()
    if not result.ok:
        print(f"ERROR: {result.detail}")
        print("The stack is up, but the app can't reach the DB through PgBouncer yet.")
        print("Double-check DATABASE_URL in .env points at port 6432.")
        sys.exit(1)

    print("  App can reach the database through PgBouncer.")


def main() -> None:
    sys.path.insert(0, str(PROJECT_ROOT))

    check_prerequisites()
    create_directories()
    start_stack()
    wait_for_postgres_healthy()
    verify_schema()

    print("\nSetup complete. Stack is running and reachable.")
    print("Run 'python infrastructure/health_check.py' anytime to re-check status.")


if __name__ == "__main__":
    main()