"""Database engine and session management"""

import logging
from contextlib import contextmanager
from typing import Generator
from sqlalchemy.pool import NullPool

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from config.settings import (
    DATABASE_URL,
    DB_MAX_OVERFLOW,
    DB_POOL_RECYCLE,
    DB_POOL_SIZE,
    DB_POOL_TIMEOUT,
)

logger = logging.getLogger(__name__)


def _create_engine(db_url: str):
    """Create engine with appropriate config for PostgreSQL or SQLite."""
    if db_url.startswith("sqlite"):
        return create_engine(
            db_url,
            poolclass=NullPool,   # PgBouncer already pools — don't double-pool
            pool_pre_ping=True,
            echo=False,
        )
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
    """
    Close all pooled connections and dispose of the engine.

    ADDED: no clean shutdown path existed before. Matters once this
    runs as a long-lived scheduler/daemon rather than one-shot scripts —
    call this on graceful shutdown (SIGTERM handler, `atexit`, etc.)
    so pooled connections aren't left open against the DB server.
    """
    engine.dispose()
    logger.info("Database engine disposed")