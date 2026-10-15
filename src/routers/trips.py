from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import current_active_user, current_optional_user
from ..database.database import get_db
from ..database.models import User
from ..schemas.trips import ListTrips, Trip, TripCreate, TripUpdate
from ..services import trips_crud

router = APIRouter(prefix="/trips", tags=["trips"])


@router.get("", response_model=ListTrips)
async def read_trips(
    db: Annotated[AsyncSession, Depends(get_db)],
    optional_user: Annotated[User | None, Depends(current_optional_user)],
    min_latitude: float = Query(...),
    max_latitude: float = Query(...),
    min_longitude: float = Query(...),
    max_longitude: float = Query(...),
    skip: int = 0,
    limit: int = 100,
    only_my_trips: bool = Query(False),
):
    """Get all trips depending on user location."""
    owner_id = None
    if only_my_trips:
        # If the user specifically asks for their trips but isn't logged in
        if optional_user is None:
            raise HTTPException(
                status_code=401,
                detail="You must be logged in to view your personal trips.",
            )
        else:
            owner_id = optional_user.id

    trips, total = await trips_crud.get_trips(
        db=db,
        min_latitude=min_latitude,
        max_latitude=max_latitude,
        min_longitude=min_longitude,
        max_longitude=max_longitude,
        skip=skip,
        limit=limit,
        owner_id=owner_id,
        viewer_id=optional_user.id if optional_user else None,
    )

    return {"trips": trips, "total": total}


@router.post("", response_model=Trip, status_code=201)
async def create_trip(
    trip: TripCreate,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(current_active_user)],
):
    """Create a new trip, user must be logged in."""
    return await trips_crud.create_trip(db=db, trip=trip, user_id=user.id)


@router.get("/{trip_uuid}", response_model=Trip)
async def read_trip(
    trip_uuid: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    optional_user: Annotated[User | None, Depends(current_optional_user)],
):
    """Get a trip detail."""
    return await trips_crud.get_trip_with_rating(
        db=db,
        trip_uuid=trip_uuid,
        viewer_id=optional_user.id if optional_user else None,
    )


@router.patch("/{trip_uuid}", response_model=Trip)
async def update_trip(
    trip_uuid: UUID,
    trip: TripUpdate,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(current_active_user)],
):
    """Update a trip detail."""
    return await trips_crud.update_trip(
        db=db, trip_uuid=trip_uuid, trip_data=trip, user_id=user.id
    )


@router.delete("/{trip_uuid}", status_code=204)
async def delete_trip(
    trip_uuid: UUID,
    db: Annotated[AsyncSession, Depends(get_db)],
    user: Annotated[User, Depends(current_active_user)],
):
    """Delete a trip."""
    await trips_crud.delete_trip(db=db, trip_uuid=trip_uuid, user_id=user.id)
