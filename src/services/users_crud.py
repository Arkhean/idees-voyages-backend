from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import models


async def delete_account(db: AsyncSession, user: models.User) -> None:
    """Delete a user's trips and anonymize their account.

    Ratings the user left on other people's trips are kept (so those trips
    keep an accurate rating history), but showing as coming from an
    anonymized, deactivated account rather than actually removing the user
    row, since ratings still reference it by foreign key.
    """
    trip_ids = select(models.Trip.id).where(models.Trip.user_id == user.id)
    await db.execute(delete(models.Rating).where(models.Rating.trip_id.in_(trip_ids)))
    await db.execute(delete(models.Trip).where(models.Trip.user_id == user.id))

    user.is_active = False
    user.is_verified = False
    user.hashed_password = ""
    user.email = f"deleted-{user.id}@deleted.local"
    user.name = "Deleted user"
    db.add(user)

    await db.commit()
