from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .auth import auth_backend, fastapi_users
from .config import config
from .database.database import engine
from .routers import ratings, trips, users
from .schemas.users import UserCreate, UserRead, UserUpdate


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Dispose of the engine on shutdown.

    The schema itself is managed by Alembic migrations (`alembic upgrade
    head`), run as a separate deploy step rather than on app startup.
    """
    yield
    await engine.dispose()


app = FastAPI(
    title="Trips API",
    description="An Async CRUD backend for managing trips with location tracking.",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=config.cors_origins_list,
    allow_credentials=False,  # auth uses a bearer token, not cookies
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(trips.router)
app.include_router(ratings.router)
app.include_router(users.router)

# Auth routes (Login, Logout)
app.include_router(
    fastapi_users.get_auth_router(auth_backend),
    prefix="/auth/jwt",
    tags=["auth"],
)

# Registration route
app.include_router(
    fastapi_users.get_register_router(UserRead, UserCreate),
    prefix="/auth",
    tags=["auth"],
)

# User management routes (Read, Update, Delete)
app.include_router(
    fastapi_users.get_users_router(UserRead, UserUpdate),
    prefix="/users",
    tags=["users"],
)

# uvicorn src.main:app --reload
