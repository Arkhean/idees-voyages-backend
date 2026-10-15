from uuid import UUID

from fastapi_users import schemas
from pydantic import Field


class UserRead(schemas.BaseUser[UUID]):
    name: str


class UserCreate(schemas.BaseUserCreate):
    name: str = Field(..., max_length=100)


class UserUpdate(schemas.BaseUserUpdate):
    name: str | None = Field(None, max_length=100)
