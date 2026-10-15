from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import current_active_user
from ..database.database import get_db
from ..database.models import User
from ..services import users_crud

router = APIRouter(prefix="/users", tags=["users"])


@router.delete("/me", status_code=204)
async def delete_my_account(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(current_active_user)],
):
    """Delete the current user's trips and anonymize their account."""
    await users_crud.delete_account(db=db, user=user)
