"""SQLAlchemy engine/session setup for the Postgres operational store."""

from __future__ import annotations

import os

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker

from life100.db.models import Base


def make_engine(database_url: str | None = None) -> Engine:
    url = database_url or os.environ.get(
        "DATABASE_URL", "postgresql+psycopg://life100:life100@localhost:5432/life100"
    )
    # Short connect timeout: when Postgres isn't up (e.g. Docker Compose not
    # running yet), callers like /simulation/start fall back to in-memory
    # quickly instead of hanging for the OS-level TCP timeout.
    return create_engine(url, pool_pre_ping=True, connect_args={"connect_timeout": 3})


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


def init_db(engine: Engine) -> None:
    """Create tables if they don't exist yet.

    Alembic migrations are out of scope for this submission (SCOPE.md) —
    `create_all` is the pragmatic floor for a 2-day build.
    """
    Base.metadata.create_all(engine)
