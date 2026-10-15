import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from src.auth import current_active_user, current_optional_user
from src.database.database import Base, enable_sqlite_foreign_keys, get_db
from src.database.models import User
from src.main import app

from .const import FIXED_MOCKED_USER_ID

TEST_ASYNC_DATABASE_URL = "sqlite+aiosqlite:///./test.db"
async_engine = create_async_engine(
    TEST_ASYNC_DATABASE_URL,
    connect_args={"check_same_thread": False},
)
enable_sqlite_foreign_keys(async_engine)
TestingAsyncSessionLocal = async_sessionmaker(async_engine, expire_on_commit=False)


mock_user = User(
    id=FIXED_MOCKED_USER_ID,
    email="testuser@example.com",
    name="Test User",
    hashed_password="hashed_dummy_password",
    is_active=True,
    is_superuser=False,
    is_verified=True,
)


@pytest.fixture(scope="function", autouse=True)
async def reset_database():
    """Recreate all tables asynchronously before every test.

    Also persists `mock_user`: `current_active_user`/`current_optional_user`
    are overridden to return it directly (bypassing a real DB-backed auth
    lookup), but any trip/rating a test attributes to `FIXED_MOCKED_USER_ID`
    still needs a matching `user` row to satisfy the foreign key.
    """
    # this could be optimized to just drop the data
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    async with TestingAsyncSessionLocal() as session:
        session.add(
            User(
                id=mock_user.id,
                email=mock_user.email,
                name=mock_user.name,
                hashed_password=mock_user.hashed_password,
                is_active=mock_user.is_active,
                is_superuser=mock_user.is_superuser,
                is_verified=mock_user.is_verified,
            )
        )
        await session.commit()
    yield
    async with async_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


async def override_get_db():
    async with TestingAsyncSessionLocal() as session:
        yield session


@pytest.fixture
async def client(reset_database):
    app.dependency_overrides[get_db] = override_get_db
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test"
    ) as ac:
        yield ac


def override_current_user():
    return mock_user


@pytest.fixture
async def auth_client(reset_database):
    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[current_active_user] = override_current_user
    app.dependency_overrides[current_optional_user] = override_current_user
    async with AsyncClient(
        transport=ASGITransport(app=app), base_url="http://test", headers={}
    ) as ac:
        yield ac

    app.dependency_overrides.clear()
