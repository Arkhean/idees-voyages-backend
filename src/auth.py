import logging
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from fastapi_users import BaseUserManager, FastAPIUsers, UUIDIDMixin
from fastapi_users.authentication import (
    AuthenticationBackend,
    BearerTransport,
    JWTStrategy,
)
from fastapi_users_db_sqlalchemy import SQLAlchemyUserDatabase
from sqlalchemy.ext.asyncio import AsyncSession

from .config import config
from .database.database import get_db
from .database.models import User

bearer_transport = BearerTransport(tokenUrl="auth/jwt/login")
logger = logging.getLogger()


async def get_user_db(session: Annotated[AsyncSession, Depends(get_db)]):
    """Dependency to inject current authenticated user to a router."""
    yield SQLAlchemyUserDatabase(session, User)


class UserManager(UUIDIDMixin, BaseUserManager[User, UUID]):
    reset_password_token_secret = config.SECRET
    verification_token_secret = config.SECRET

    async def on_after_register(self, user: User, request=None):
        """Log successful user registration."""
        logger.info(f"User {user.email} registered.")  # pragma: no cover


async def get_user_manager(
    user_db: Annotated[SQLAlchemyUserDatabase, Depends(get_user_db)],
):
    """Dependency providing the user manager used by fastapi-users."""
    yield UserManager(user_db)


def get_jwt_strategy() -> JWTStrategy:
    """Build the JWT strategy used to sign and verify access tokens."""
    # Token expires in 1 hour (3600 seconds)
    return JWTStrategy(secret=config.SECRET, lifetime_seconds=3600)


auth_backend = AuthenticationBackend(
    name="jwt",
    transport=bearer_transport,
    get_strategy=get_jwt_strategy,
)


fastapi_users = FastAPIUsers[User, UUID](
    get_user_manager,
    [auth_backend],
)

# This dependency ensures the route is only accessible to logged-in users
current_active_user = fastapi_users.current_user(active=True)
# This dependency ensures the route do not throw a 401 if user is not logged-in
current_optional_user = fastapi_users.current_user(optional=True)
