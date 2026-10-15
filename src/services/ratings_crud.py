from collections.abc import Sequence
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import models


async def create_rating(
    db: AsyncSession, rating: int, user_id: UUID, trip_id: int, comment: str
) -> models.Rating:
    """Create a rating, raising 409 if this user already rated this trip."""
    db_rating = models.Rating(
        user_id=user_id, rating=rating, trip_id=trip_id, comment=comment
    )
    db.add(db_rating)
    try:
        await db.commit()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(
            status_code=409, detail="You have already rated this trip."
        ) from exc
    await db.refresh(db_rating)
    return db_rating


async def update_rating(
    db: AsyncSession, rating: int, user_id: UUID, trip_id: int, comment: str
) -> models.Rating:
    """Update an existing rating, raising 404 if none exists yet."""
    query = select(models.Rating).where(
        models.Rating.user_id == user_id, models.Rating.trip_id == trip_id
    )
    db_rating = (await db.execute(query)).scalar_one_or_none()

    if db_rating is None:
        raise HTTPException(status_code=404, detail="Rating not found")

    db_rating.rating = rating
    db_rating.comment = comment

    db.add(db_rating)
    await db.commit()
    await db.refresh(db_rating)

    return db_rating


async def delete_rating(db: AsyncSession, trip_id: int, user_id: UUID) -> None:
    """Delete a user's rating for a trip, if one exists."""
    query = delete(models.Rating).where(
        models.Rating.trip_id == trip_id, models.Rating.user_id == user_id
    )
    await db.execute(query)
    await db.commit()


async def get_ratings(
    db: AsyncSession, trip_id: int, skip: int = 0, limit: int = 100
) -> tuple[Sequence[models.Rating], int]:
    """List a trip's ratings (most recent first), each with the rater's name attached.

    Returns the page of ratings alongside the total count for the trip
    (ignoring `skip`/`limit`), for pagination.
    """
    total_query = (
        select(func.count())
        .select_from(models.Rating)
        .where(models.Rating.trip_id == trip_id)
    )
    total = (await db.execute(total_query)).scalar_one()

    query = (
        select(models.Rating, models.User.name)
        .join(models.User, models.User.id == models.Rating.user_id)
        .where(models.Rating.trip_id == trip_id)
        .order_by(models.Rating.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    rows = (await db.execute(query)).all()

    ratings = []
    for rating, user_name in rows:
        rating.user_name = user_name
        ratings.append(rating)
    return ratings, total
