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
    """Create engine configured correctly for SQLite, direct Postgres, or PgBouncer."""
    if db_url.startswith("sqlite"):
        return create_engine(
            db_url,
            echo=False,
            connect_args={"check_same_thread": False},
        )

    # Auto-detect PgBouncer by port/name in the URL — kept from the
    # proposed db.py, this is a genuine improvement over a manual flag.
    is_pgbouncer = ":6432" in db_url or "pgbouncer" in db_url

    if is_pgbouncer:
        # NullPool: PgBouncer (transaction pool_mode) is already the
        # connection pool for Postgres. Layering SQLAlchemy's own pool
        # on top double-pools and risks session-level state (prepared
        # statements, SET commands) leaking across what SQLAlchemy
        # thinks is one held connection but PgBouncer is actually
        # swapping between transactions.
        #
        # NOTE: an earlier draft added connect_args={"prepare_threshold":
        # None} here, intending to disable psycopg's automatic prepared
        # statements under PgBouncer. That option is psycopg3-only —
        # this project's DATABASE_URL uses psycopg2 throughout, where
        # it's silently dropped (psycopg2 skips None-valued kwargs
        # before they reach libpq) rather than doing anything. Left out
        # here since it was dead code, not a working fix. If this
        # project moves to psycopg3, prepared-statement handling under
        # PgBouncer's transaction mode should be revisited properly then.
        return create_engine(
            db_url,
            poolclass=NullPool,
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
    """Close all pooled connections and dispose of the engine cleanly."""
    engine.dispose()
    logger.info("Database engine disposed")