"""Database engine and session management"""

import logging
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool

from config.settings import (
    DATABASE_URL,
    DB_MAX_OVERFLOW,
    DB_POOL_RECYCLE,
    DB_POOL_SIZE,
    DB_POOL_TIMEOUT,
)

logger = logging.getLogger(__name__)


def _create_engine(db_url: str):
    """Create engine configured correctly for SQLite, Direct Postgres, or PgBouncer."""
    if db_url.startswith("sqlite"):
        return create_engine(
            db_url,
            connect_args={"check_same_thread": False} if ":memory:" in db_url else {},
            echo=False,
        )

    # Check if connecting through PgBouncer (default port 6432)
    is_pgbouncer = ":6432" in db_url or "pgbouncer" in db_url

    if is_pgbouncer:
        # Transaction-mode PgBouncer: Use NullPool and disable client-side prepared statements
        return create_engine(
            db_url,
            poolclass=NullPool,
            connect_args={
                "prepare_threshold": None  # Disables prepared statements for psycopg3 / asyncpg compatibility
            },
            echo=False,
        )

    # Direct PostgreSQL connection
    return create_engine(
        db_url,
        pool_size=DB_POOL_SIZE,
        max_overflow=DB_MAX_OVERFLOW,
        pool_recycle=DB_POOL_RECYCLE,
        pool_pre_ping=True,
        pool_timeout=DB_POOL_TIMEOUT,
        echo=False,
    )


engine = _create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Yield a database session with automatic commit/rollback."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        logger.exception("Database session failed, rolling back")
        session.rollback()
        raise
    finally:
        session.close()


def dispose_engine() -> None:
    """Close all pooled connections and dispose of the engine cleanly."""
    engine.dispose()
    logger.info("Database engine disposed")