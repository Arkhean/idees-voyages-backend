import uuid
from collections.abc import Sequence
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import delete, func, or_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from ..database import models
from ..schemas.trips import TripCreate, TripUpdate


def _ratings_aggregate_subquery():
    """One row per rated trip: mean rating and number of raters.

    Grouping ratings once here lets list queries LEFT JOIN against it in a
    single pass instead of issuing a per-trip aggregate query (N+1).
    """
    return (
        select(
            models.Rating.trip_id.label("trip_id"),
            func.avg(models.Rating.rating).label("mean_rating"),
            func.count(models.Rating.rating).label("rating_people_number"),
        )
        .group_by(models.Rating.trip_id)
        .subquery()
    )


def _attach_rating_aggregate(
    trip: models.Trip, mean_rating: float | None, rating_people_number: int
) -> models.Trip:
    trip.mean_rating = round(mean_rating, 1) if mean_rating is not None else 0.0
    trip.rating_people_number = rating_people_number
    return trip


def _attach_is_owner(trip: models.Trip, viewer_id: UUID | None) -> models.Trip:
    """Attach whether `viewer_id` owns this trip, e.g. to gate an edit button client-side."""
    trip.is_owner = viewer_id is not None and trip.user_id == viewer_id
    return trip


async def _get_trip_rating_aggregate(
    db: AsyncSession, trip_id: int
) -> tuple[float, int]:
    """Aggregate for a single trip, used for the write endpoints (create/update)."""
    query = select(
        func.coalesce(func.avg(models.Rating.rating), 0.0),
        func.coalesce(func.count(models.Rating.rating), 0),
    ).where(models.Rating.trip_id == trip_id)
    mean_rating, rating_people_number = (await db.execute(query)).one()
    return round(mean_rating, 1), rating_people_number


def _trips_filter_conditions(
    min_latitude: float,
    max_latitude: float,
    min_longitude: float,
    max_longitude: float,
    owner_id: UUID | None,
    viewer_id: UUID | None,
):
    """Build the WHERE conditions shared by the list and count queries.

    Private trips are excluded unless they belong to `owner_id` (the
    "only my trips" filter) or to `viewer_id` (the logged-in caller, who can
    always see their own private trips even when browsing all trips).
    """
    conditions = [
        models.Trip.latitude >= min_latitude,
        models.Trip.latitude <= max_latitude,
        models.Trip.longitude >= min_longitude,
        models.Trip.longitude <= max_longitude,
    ]

    if owner_id is not None:
        conditions.append(models.Trip.user_id == owner_id)
    elif viewer_id is not None:
        conditions.append(
            or_(models.Trip.is_private.is_(False), models.Trip.user_id == viewer_id)
        )
    else:
        conditions.append(models.Trip.is_private.is_(False))

    return conditions


async def get_trips(
    db: AsyncSession,
    min_latitude: float,
    max_latitude: float,
    min_longitude: float,
    max_longitude: float,
    skip: int = 0,
    limit: int = 100,
    owner_id: UUID | None = None,
    viewer_id: UUID | None = None,
) -> tuple[Sequence[models.Trip], int]:
    """List trips within a bounding box, each with its rating aggregate attached.

    Returns the page of trips alongside the total count matching the
    filters (ignoring `skip`/`limit`), for pagination.
    """
    conditions = _trips_filter_conditions(
        min_latitude=min_latitude,
        max_latitude=max_latitude,
        min_longitude=min_longitude,
        max_longitude=max_longitude,
        owner_id=owner_id,
        viewer_id=viewer_id,
    )

    total_query = select(func.count()).select_from(models.Trip).where(*conditions)
    total = (await db.execute(total_query)).scalar_one()

    ratings_agg = _ratings_aggregate_subquery()
    query = (
        select(
            models.Trip,
            ratings_agg.c.mean_rating,
            ratings_agg.c.rating_people_number,
        )
        .outerjoin(ratings_agg, models.Trip.id == ratings_agg.c.trip_id)
        .where(*conditions)
        .offset(skip)
        .limit(limit)
    )

    rows = (await db.execute(query)).all()
    trips = [
        _attach_is_owner(
            trip=_attach_rating_aggregate(
                trip=trip,
                mean_rating=mean_rating,
                rating_people_number=rating_people_number or 0,
            ),
            viewer_id=viewer_id,
        )
        for trip, mean_rating, rating_people_number in rows
    ]
    return trips, total


async def get_trip(
    db: AsyncSession, trip_uuid: UUID, user_id: UUID | None = None
) -> models.Trip:
    """Get trip by trip_id and handle 404 and 403."""
    query = select(models.Trip).filter(models.Trip.uuid == trip_uuid)
    trip = (await db.execute(query)).scalar_one_or_none()

    if trip is None:
        raise HTTPException(status_code=404, detail="Trip not found.")

    if user_id is not None and trip.user_id != user_id:
        raise HTTPException(status_code=403, detail="Forbidden.")

    return trip


async def get_trip_with_rating(
    db: AsyncSession, trip_uuid: UUID, viewer_id: UUID | None = None
) -> models.Trip:
    """Get trip by uuid with its rating aggregate attached, for read responses.

    Raises 404 for a private trip that doesn't belong to the viewer, so a
    private trip's existence isn't revealed to anyone but its creator.
    """
    trip = await get_trip(db=db, trip_uuid=trip_uuid)
    if trip.is_private and trip.user_id != viewer_id:
        raise HTTPException(status_code=404, detail="Trip not found.")
    mean_rating, rating_people_number = await _get_trip_rating_aggregate(
        db=db, trip_id=trip.id
    )
    trip = _attach_rating_aggregate(
        trip=trip, mean_rating=mean_rating, rating_people_number=rating_people_number
    )
    return _attach_is_owner(trip=trip, viewer_id=viewer_id)


async def create_trip(db: AsyncSession, trip: TripCreate, user_id: UUID) -> models.Trip:
    """Create a trip owned by the given user."""
    db_trip = models.Trip(**trip.model_dump(), user_id=user_id, uuid=uuid.uuid4())
    db.add(db_trip)
    await db.commit()
    await db.refresh(db_trip)
    # A brand new trip cannot have any ratings yet, and its creator always owns it.
    db_trip = _attach_rating_aggregate(trip=db_trip, mean_rating=None, rating_people_number=0)
    return _attach_is_owner(trip=db_trip, viewer_id=user_id)


async def update_trip(
    db: AsyncSession, trip_uuid: UUID, trip_data: TripUpdate, user_id: UUID
) -> models.Trip:
    """Update a trip owned by the given user, handling 404 and 403."""
    db_trip = await get_trip(db=db, trip_uuid=trip_uuid, user_id=user_id)
    update_data = trip_data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_trip, key, value)
    await db.commit()
    await db.refresh(db_trip)
    mean_rating, rating_people_number = await _get_trip_rating_aggregate(
        db=db, trip_id=db_trip.id
    )
    db_trip = _attach_rating_aggregate(
        trip=db_trip, mean_rating=mean_rating, rating_people_number=rating_people_number
    )
    return _attach_is_owner(trip=db_trip, viewer_id=user_id)


async def delete_trip(db: AsyncSession, trip_uuid: UUID, user_id: UUID) -> models.Trip:
    """Delete a trip (and its ratings) owned by the given user, handling 404 and 403.

    Ratings are deleted explicitly rather than relying on the database's
    `ON DELETE CASCADE`, so behavior doesn't depend on whether the target
    database actually enforces foreign keys (e.g. SQLite doesn't, by
    default).
    """
    db_trip = await get_trip(db=db, trip_uuid=trip_uuid, user_id=user_id)
    await db.execute(delete(models.Rating).where(models.Rating.trip_id == db_trip.id))
    await db.delete(db_trip)
    await db.commit()
    return db_trip
