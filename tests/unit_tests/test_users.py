from sqlalchemy import select

from src.auth import current_active_user, current_optional_user
from src.database.models import Rating, Trip, User
from src.main import app

from ..conftest import TestingAsyncSessionLocal
from ..factories import RatingFactory, TripFactory, UserFactory


async def test_register_user_return_201(client):
    payload = {
        "email": "newuser@example.com",
        "password": "a-strong-password123",
        "name": "Jane Doe",
    }
    response = await client.post("/auth/register", json=payload)
    assert response.status_code == 201
    response = response.json()
    assert response["email"] == payload["email"]
    assert response["name"] == payload["name"]
    assert "id" in response


async def test_register_user_missing_name_return_422(client):
    payload = {
        "email": "newuser2@example.com",
        "password": "a-strong-password123",
    }
    response = await client.post("/auth/register", json=payload)
    assert response.status_code == 422


# delete account #######################################################################


def _override_current_user(user):
    """Override current_active_user/current_optional_user with a real persisted user."""

    def _get_user():
        return user

    app.dependency_overrides[current_active_user] = _get_user
    app.dependency_overrides[current_optional_user] = _get_user


async def test_delete_account_return_204(auth_client):
    user = await UserFactory.create_async()
    other_user = await UserFactory.create_async()
    _override_current_user(user)

    my_trip = await TripFactory.create_async(user_id=user.id)
    other_trip = await TripFactory.create_async(user_id=other_user.id)
    await RatingFactory.create_async(trip_id=my_trip.id, user_id=other_user.id)
    my_rating_on_other_trip = await RatingFactory.create_async(
        trip_id=other_trip.id, user_id=user.id
    )

    response = await auth_client.delete("/users/me")
    assert response.status_code == 204

    async with TestingAsyncSessionLocal() as db:
        remaining_trips = (await db.execute(select(Trip))).scalars().all()
        assert [trip.id for trip in remaining_trips] == [other_trip.id]

        remaining_ratings = (await db.execute(select(Rating))).scalars().all()
        assert [rating.trip_id for rating in remaining_ratings] == [
            my_rating_on_other_trip.trip_id
        ]

        db_user = await db.get(User, user.id)
        assert db_user.is_active is False
        assert db_user.is_verified is False
        assert db_user.hashed_password == ""
        assert db_user.email == f"deleted-{user.id}@deleted.local"
        assert db_user.name == "Deleted user"


async def test_delete_account_not_authenticated_return_401(client):
    response = await client.delete("/users/me")
    assert response.status_code == 401
