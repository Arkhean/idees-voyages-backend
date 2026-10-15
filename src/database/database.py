from sqlalchemy import StaticPool, event
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

from src.config import config


def enable_sqlite_foreign_keys(target_engine: AsyncEngine) -> None:
    """Turn on foreign key enforcement for a SQLite engine.

    SQLite ignores FOREIGN KEY constraints unless this pragma is set on each
    connection, unlike every other supported database (e.g. PostgreSQL),
    which always enforces them. Without this, code relying on FK behavior
    (e.g. `ON DELETE CASCADE`, or rejecting an invalid reference) would only
    actually be exercised in production, not locally or in tests.
    """

    @event.listens_for(target_engine.sync_engine, "connect")
    def _set_sqlite_pragma(dbapi_connection, connection_record):  # pragma: no cover
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


_engine_kwargs = {}
if config.DATABASE_URL.startswith("sqlite"):  # pragma: no cover
    _engine_kwargs["connect_args"] = {"check_same_thread": False}
    if ":memory:" in config.DATABASE_URL:
        # An in-memory sqlite database only exists on a single connection,
        # so all sessions must share that one connection via a StaticPool.
        _engine_kwargs["poolclass"] = StaticPool

engine = create_async_engine(config.DATABASE_URL, **_engine_kwargs)
if config.DATABASE_URL.startswith("sqlite"):  # pragma: no cover
    enable_sqlite_foreign_keys(engine)

SessionLocal = async_sessionmaker(
    autocommit=False, autoflush=False, bind=engine, class_=AsyncSession
)


class Base(DeclarativeBase):
    pass


# Async dependency
async def get_db():  # pragma: no cover
    """Create an async session."""
    async with SessionLocal() as db:
        try:
            yield db
        finally:
            await db.close()
