import uuid
from datetime import UTC, datetime

from ..const import FIXED_MOCKED_USER_ID
from ..factories import RatingFactory, TripFactory, UserFactory

# list ratings #########################################################################


async def test_list_ratings_return_200(client):
    trip = await TripFactory.create_async()
    rater = await UserFactory.create_async(name="Alice")
    await RatingFactory.create_async(
        trip_id=trip.id, user_id=rater.id, rating=5, comment="Amazing trip!"
    )

    response = await client.get(f"/trips/{trip.uuid}/ratings")
    assert response.status_code == 200
    response = response.json()
    assert response["total"] == 1
    assert len(response["ratings"]) == 1
    assert response["ratings"][0]["user_id"] == str(rater.id)
    assert response["ratings"][0]["user_name"] == "Alice"
    assert response["ratings"][0]["rating"] == 5
    assert response["ratings"][0]["comment"] == "Amazing trip!"


async def test_list_ratings_orders_most_recent_first(client):
    trip = await TripFactory.create_async()
    older_rater = await UserFactory.create_async()
    newer_rater = await UserFactory.create_async()
    await RatingFactory.create_async(
        trip_id=trip.id,
        user_id=older_rater.id,
        created_at=datetime(2020, 1, 1, tzinfo=UTC),
    )
    await RatingFactory.create_async(
        trip_id=trip.id,
        user_id=newer_rater.id,
        created_at=datetime(2024, 1, 1, tzinfo=UTC),
    )

    response = await client.get(f"/trips/{trip.uuid}/ratings")
    assert response.status_code == 200
    response = response.json()
    assert [r["user_id"] for r in response["ratings"]] == [
        str(newer_rater.id),
        str(older_rater.id),
    ]


async def test_list_ratings_total_ignores_limit(client):
    trip = await TripFactory.create_async()
    for _ in range(3):
        rater = await UserFactory.create_async()
        await RatingFactory.create_async(trip_id=trip.id, user_id=rater.id)

    response = await client.get(f"/trips/{trip.uuid}/ratings", params={"limit": 1})
    assert response.status_code == 200
    response = response.json()
    assert response["total"] == 3
    assert len(response["ratings"]) == 1


async def test_list_ratings_trip_not_found_return_404(client):
    response = await client.get(f"/trips/{uuid.uuid4()}/ratings")
    assert response.status_code == 404


async def test_list_ratings_private_trip_not_owner_return_404(client):
    trip = await TripFactory.create_async(is_private=True)
    response = await client.get(f"/trips/{trip.uuid}/ratings")
    assert response.status_code == 404


async def test_list_ratings_private_trip_owner_return_200(auth_client):
    trip = await TripFactory.create_async(
        user_id=FIXED_MOCKED_USER_ID, is_private=True
    )
    rater = await UserFactory.create_async()
    await RatingFactory.create_async(trip_id=trip.id, user_id=rater.id)

    response = await auth_client.get(f"/trips/{trip.uuid}/ratings")
    assert response.status_code == 200
    response = response.json()
    assert response["total"] == 1


# create rating #########################################################################


async def test_create_rating_return_201(auth_client):
    trip = await TripFactory.create_async()
    payload = {"rating": 4, "comment": "Great trip, would recommend!"}
    response = await auth_client.post(f"/trips/{trip.uuid}/ratings", json=payload)
    assert response.status_code == 201
    response = response.json()
    assert response["rating"] == payload["rating"]
    assert response["comment"] == payload["comment"]


async def test_create_rating_trip_not_found_return_404(auth_client):
    response = await auth_client.post(
        f"/trips/{uuid.uuid4()}/ratings",
        json={"rating": 4, "comment": "Great trip!"},
    )
    assert response.status_code == 404


async def test_create_rating_not_authenticated_return_401(client):
    trip = await TripFactory.create_async()
    response = await client.post(
        f"/trips/{trip.uuid}/ratings",
        json={"rating": 4, "comment": "Great trip!"},
    )
    assert response.status_code == 401


async def test_create_rating_invalid_rating_return_422(auth_client):
    trip = await TripFactory.create_async()
    response = await auth_client.post(
        f"/trips/{trip.uuid}/ratings",
        json={"rating": 6, "comment": "Out of range rating."},
    )
    assert response.status_code == 422


async def test_create_rating_private_trip_return_404(auth_client):
    trip = await TripFactory.create_async(is_private=True)
    response = await auth_client.post(
        f"/trips/{trip.uuid}/ratings",
        json={"rating": 5, "comment": "Rating someone else's private trip."},
    )
    assert response.status_code == 404


async def test_create_rating_own_trip_return_403(auth_client):
    trip = await TripFactory.create_async(user_id=FIXED_MOCKED_USER_ID)
    response = await auth_client.post(
        f"/trips/{trip.uuid}/ratings",
        json={"rating": 5, "comment": "Rating my own trip."},
    )
    assert response.status_code == 403


async def test_create_rating_twice_return_409(auth_client):
    trip = await TripFactory.create_async()
    await RatingFactory.create_async(trip_id=trip.id, user_id=FIXED_MOCKED_USER_ID)

    response = await auth_client.post(
        f"/trips/{trip.uuid}/ratings",
        json={"rating": 4, "comment": "Trying to rate a second time."},
    )
    assert response.status_code == 409


# update rating #########################################################################


async def test_update_rating_return_200(auth_client):
    trip = await TripFactory.create_async()
    await RatingFactory.create_async(
        trip_id=trip.id, user_id=FIXED_MOCKED_USER_ID, rating=3, comment="It was okay."
    )

    new_payload = {"rating": 5, "comment": "Actually, it was amazing!"}
    response = await auth_client.put(f"/trips/{trip.uuid}/ratings", json=new_payload)
    assert response.status_code == 200
    response = response.json()
    assert response["rating"] == new_payload["rating"]
    assert response["comment"] == new_payload["comment"]


async def test_update_rating_private_trip_return_404(auth_client):
    trip = await TripFactory.create_async(is_private=True)
    response = await auth_client.put(
        f"/trips/{trip.uuid}/ratings",
        json={"rating": 5, "comment": "Rating someone else's private trip."},
    )
    assert response.status_code == 404


async def test_update_rating_own_trip_return_403(auth_client):
    trip = await TripFactory.create_async(user_id=FIXED_MOCKED_USER_ID)
    response = await auth_client.put(
        f"/trips/{trip.uuid}/ratings",
        json={"rating": 5, "comment": "Rating my own trip."},
    )
    assert response.status_code == 403


async def test_update_rating_trip_not_found_return_404(auth_client):
    response = await auth_client.put(
        f"/trips/{uuid.uuid4()}/ratings",
        json={"rating": 5, "comment": "Updated comment."},
    )
    assert response.status_code == 404


async def test_update_rating_not_found_return_404(auth_client):
    trip = await TripFactory.create_async()
    response = await auth_client.put(
        f"/trips/{trip.uuid}/ratings",
        json={"rating": 5, "comment": "No rating exists yet."},
    )
    assert response.status_code == 404


async def test_update_rating_not_authenticated_return_401(client):
    trip = await TripFactory.create_async()
    response = await client.put(
        f"/trips/{trip.uuid}/ratings",
        json={"rating": 5, "comment": "Updated comment."},
    )
    assert response.status_code == 401


# delete rating #########################################################################


async def test_delete_rating_return_204(auth_client):
    trip = await TripFactory.create_async()
    await RatingFactory.create_async(trip_id=trip.id, user_id=FIXED_MOCKED_USER_ID)

    response = await auth_client.delete(f"/trips/{trip.uuid}/ratings")
    assert response.status_code == 204


async def test_delete_rating_private_trip_return_404(auth_client):
    trip = await TripFactory.create_async(is_private=True)
    response = await auth_client.delete(f"/trips/{trip.uuid}/ratings")
    assert response.status_code == 404


async def test_delete_rating_trip_not_found_return_404(auth_client):
    response = await auth_client.delete(f"/trips/{uuid.uuid4()}/ratings")
    assert response.status_code == 404


async def test_delete_rating_not_authenticated_return_401(client):
    trip = await TripFactory.create_async()
    response = await client.delete(f"/trips/{trip.uuid}/ratings")
    assert response.status_code == 401
