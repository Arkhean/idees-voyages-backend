from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import current_active_user, current_optional_user
from ..database import models
from ..database.database import get_db
from ..database.models import User
from ..schemas.ratings import ListRatings, Rating
from ..services import ratings_crud, trips_crud

router = APIRouter(prefix="/trips/{trip_uuid}/ratings", tags=["Ratings"])


def _ensure_trip_visible(trip: models.Trip, user: User | None) -> None:
    """Raise 404 for a private trip that doesn't belong to the user.

    Mirrors the visibility rule used for reading a trip: a private trip
    doesn't exist as far as anyone but its creator is concerned, so its
    ratings can't be read or added to by anyone else either.
    """
    if trip.is_private and (user is None or trip.user_id != user.id):
        raise HTTPException(status_code=404, detail="Trip not found.")


@router.get("", response_model=ListRatings)
async def list_ratings(
    db: Annotated[AsyncSession, Depends(get_db)],
    optional_user: Annotated[User | None, Depends(current_optional_user)],
    trip_uuid: UUID,
    skip: int = 0,
    limit: int = 100,
):
    """List a trip's ratings, most recent first."""
    trip = await trips_crud.get_trip(db=db, trip_uuid=trip_uuid)
    _ensure_trip_visible(trip=trip, user=optional_user)
    ratings, total = await ratings_crud.get_ratings(
        db=db, trip_id=trip.id, skip=skip, limit=limit
    )
    return {"ratings": ratings, "total": total}


@router.post("", response_model=Rating, status_code=201)
async def post_rating(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(current_active_user)],
    trip_uuid: UUID,
    body: Rating,
):
    """Rate a trip, user must be logged in and not have rated it yet."""
    trip = await trips_crud.get_trip(db=db, trip_uuid=trip_uuid)
    _ensure_trip_visible(trip=trip, user=user)
    if trip.user_id == user.id:
        raise HTTPException(status_code=403, detail="You cannot rate your own trip.")
    await ratings_crud.create_rating(
        db=db,
        trip_id=trip.id,
        user_id=user.id,
        rating=body.rating,
        comment=body.comment,
    )
    return body


@router.put("", response_model=Rating, status_code=200)
async def update_rating(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(current_active_user)],
    trip_uuid: UUID,
    body: Rating,
):
    """Update the current user's existing rating for a trip."""
    trip = await trips_crud.get_trip(db=db, trip_uuid=trip_uuid)
    _ensure_trip_visible(trip=trip, user=user)
    if trip.user_id == user.id:
        raise HTTPException(status_code=403, detail="You cannot rate your own trip.")
    await ratings_crud.update_rating(
        db=db,
        trip_id=trip.id,
        user_id=user.id,
        rating=body.rating,
        comment=body.comment,
    )
    return body


@router.delete("", status_code=204)
async def delete_rating(
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(current_active_user)],
    trip_uuid: UUID,
):
    """Delete the current user's rating for a trip."""
    trip = await trips_crud.get_trip(db=db, trip_uuid=trip_uuid)
    _ensure_trip_visible(trip=trip, user=user)
    await ratings_crud.delete_rating(db=db, trip_id=trip.id, user_id=user.id)
