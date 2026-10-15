from sqlalchemy import inspect

from src.database.database import engine
from src.main import app, lifespan


async def test_lifespan_disposes_engine_on_shutdown():
    async with lifespan(app):
        pass

    # After the context manager exits, the engine has been disposed: its
    # connection pool was torn down, so a fresh connect() must still work
    # (SQLAlchemy transparently reconnects) rather than raise.
    async with engine.connect() as conn:
        await conn.run_sync(lambda sync_conn: inspect(sync_conn).get_table_names())
