import uuid

from ..const import FIXED_MOCKED_USER_ID
from ..factories import RatingFactory, TripFactory

# list trips ##########################################################################


async def test_list_trips_return_200(client):
    trip = await TripFactory.create_async()
    response = await client.get(
        "/trips",
        params={
            "min_latitude": trip.latitude - 10,
            "max_latitude": trip.latitude + 10,
            "min_longitude": trip.longitude - 10,
            "max_longitude": trip.longitude + 10,
        },
    )
    assert response.status_code == 200
    response = response.json()
    assert response["total"] == 1
    assert len(response["trips"]) == 1
    assert response["trips"][0]["uuid"] == str(trip.uuid)
    assert response["trips"][0]["title"] == trip.title
    assert response["trips"][0]["latitude"] == trip.latitude
    assert response["trips"][0]["longitude"] == trip.longitude
    assert response["trips"][0]["description"] == trip.description
    assert response["trips"][0]["start_date"] == str(trip.start_date)
    assert response["trips"][0]["end_date"] == str(trip.end_date)
    assert response["trips"][0]["mean_rating"] == 0
    assert response["trips"][0]["rating_people_number"] == 0
    assert response["trips"][0]["is_owner"] is False


async def test_list_trips_marks_own_trip_as_owner(auth_client):
    trip = await TripFactory.create_async(user_id=FIXED_MOCKED_USER_ID)
    response = await auth_client.get(
        "/trips",
        params={
            "min_latitude": trip.latitude - 10,
            "max_latitude": trip.latitude + 10,
            "min_longitude": trip.longitude - 10,
            "max_longitude": trip.longitude + 10,
        },
    )
    assert response.status_code == 200
    response = response.json()
    assert response["trips"][0]["is_owner"] is True


async def test_list_trips_total_ignores_limit(client):
    trip = await TripFactory.create_async()
    await TripFactory.create_async(latitude=trip.latitude, longitude=trip.longitude)
    await TripFactory.create_async(latitude=trip.latitude, longitude=trip.longitude)

    response = await client.get(
        "/trips",
        params={
            "min_latitude": trip.latitude - 10,
            "max_latitude": trip.latitude + 10,
            "min_longitude": trip.longitude - 10,
            "max_longitude": trip.longitude + 10,
            "limit": 1,
        },
    )
    assert response.status_code == 200
    response = response.json()
    assert response["total"] == 3
    assert len(response["trips"]) == 1


async def test_list_trips_returns_rating_aggregate(client):
    trip = await TripFactory.create_async()
    await RatingFactory.create_async(trip_id=trip.id, rating=5)
    await RatingFactory.create_async(trip_id=trip.id, rating=2)

    response = await client.get(
        "/trips",
        params={
            "min_latitude": trip.latitude - 10,
            "max_latitude": trip.latitude + 10,
            "min_longitude": trip.longitude - 10,
            "max_longitude": trip.longitude + 10,
        },
    )
    assert response.status_code == 200
    response = response.json()
    assert response["trips"][0]["mean_rating"] == 3.5
    assert response["trips"][0]["rating_people_number"] == 2


async def test_list_trips_excludes_others_private_trips(client):
    trip = await TripFactory.create_async(is_private=True)
    response = await client.get(
        "/trips",
        params={
            "min_latitude": trip.latitude - 10,
            "max_latitude": trip.latitude + 10,
            "min_longitude": trip.longitude - 10,
            "max_longitude": trip.longitude + 10,
        },
    )
    assert response.status_code == 200
    response = response.json()
    assert response["total"] == 0
    assert response["trips"] == []


async def test_list_trips_includes_own_private_trips(auth_client):
    trip = await TripFactory.create_async(
        user_id=FIXED_MOCKED_USER_ID, is_private=True
    )
    response = await auth_client.get(
        "/trips",
        params={
            "min_latitude": trip.latitude - 10,
            "max_latitude": trip.latitude + 10,
            "min_longitude": trip.longitude - 10,
            "max_longitude": trip.longitude + 10,
        },
    )
    assert response.status_code == 200
    response = response.json()
    assert response["total"] == 1
    assert response["trips"][0]["uuid"] == str(trip.uuid)


async def test_list_trips_near_the_location(client):
    trip = await TripFactory.create_async()
    await TripFactory.create_async(
        latitude=trip.latitude + 20,  # far
        longitude=trip.longitude,
    )
    response = await client.get(
        "/trips",
        params={
            "min_latitude": trip.latitude - 10,
            "max_latitude": trip.latitude + 10,
            "min_longitude": trip.longitude - 10,
            "max_longitude": trip.longitude + 10,
        },
    )
    assert response.status_code == 200
    response = response.json()
    assert response["total"] == 1
    assert len(response["trips"]) == 1
    assert response["trips"][0]["uuid"] == str(trip.uuid)


async def test_list_trips_only_my_trips_return_401(client):
    response = await client.get(
        "/trips",
        params={
            "min_latitude": -10,
            "max_latitude": 10,
            "min_longitude": -10,
            "max_longitude": 10,
            "only_my_trips": True,
        },
    )
    assert response.status_code == 401


async def test_list_trips_only_my_trips_return_200(auth_client):
    my_trip = await TripFactory.create_async(user_id=FIXED_MOCKED_USER_ID)
    await TripFactory.create_async(
        latitude=my_trip.latitude, longitude=my_trip.longitude
    )
    response = await auth_client.get(
        "/trips",
        params={
            "min_latitude": my_trip.latitude - 10,
            "max_latitude": my_trip.latitude + 10,
            "min_longitude": my_trip.longitude - 10,
            "max_longitude": my_trip.longitude + 10,
            "only_my_trips": True,
        },
    )
    assert response.status_code == 200
    response = response.json()
    assert response["total"] == 1
    assert len(response["trips"]) == 1
    assert response["trips"][0]["uuid"] == str(my_trip.uuid)


# get trip by id ######################################################################


async def test_get_trip_return_200(client):
    trip = await TripFactory.create_async()
    response = await client.get(f"/trips/{trip.uuid}")
    assert response.status_code == 200
    response = response.json()
    assert response["uuid"] == str(trip.uuid)
    assert response["title"] == trip.title
    assert response["latitude"] == trip.latitude
    assert response["longitude"] == trip.longitude
    assert response["description"] == trip.description
    assert response["start_date"] == str(trip.start_date)
    assert response["end_date"] == str(trip.end_date)
    assert response["mean_rating"] == 0
    assert response["rating_people_number"] == 0
    assert response["is_owner"] is False


async def test_get_trip_returns_rating_aggregate(client):
    trip = await TripFactory.create_async()
    await RatingFactory.create_async(trip_id=trip.id, rating=5)
    await RatingFactory.create_async(trip_id=trip.id, rating=2)

    response = await client.get(f"/trips/{trip.uuid}")
    assert response.status_code == 200
    response = response.json()
    assert response["mean_rating"] == 3.5
    assert response["rating_people_number"] == 2


async def test_get_trip_private_not_owner_return_404(client):
    trip = await TripFactory.create_async(is_private=True)
    response = await client.get(f"/trips/{trip.uuid}")
    assert response.status_code == 404


async def test_get_trip_private_owner_return_200(auth_client):
    trip = await TripFactory.create_async(
        user_id=FIXED_MOCKED_USER_ID, is_private=True
    )
    response = await auth_client.get(f"/trips/{trip.uuid}")
    assert response.status_code == 200
    response = response.json()
    assert response["uuid"] == str(trip.uuid)
    assert response["is_owner"] is True


async def test_get_trip_return_404(client):
    response = await client.get(f"/trips/{uuid.uuid4()}")
    assert response.status_code == 404


# create trip #########################################################################


async def test_create_trip_return_201(auth_client):
    payload = {
        "latitude": 48.8566,
        "longitude": 2.3522,
        "title": "Trip to Paris",
        "description": "A wonderful trip to the city of lights.",
        "addresses": ["Paris, France"],
        "start_date": "2026-09-01",
        "end_date": "2026-09-05",
        "is_private": False,
    }
    response = await auth_client.post("/trips", json=payload)
    assert response.status_code == 201
    response = response.json()
    assert response["title"] == payload["title"]
    assert response["description"] == payload["description"]
    assert response["latitude"] == payload["latitude"]
    assert response["longitude"] == payload["longitude"]
    assert response["addresses"] == payload["addresses"]
    assert response["start_date"] == payload["start_date"]
    assert response["end_date"] == payload["end_date"]
    assert response["is_private"] == payload["is_private"]
    assert response["is_owner"] is True
    assert "uuid" in response


async def test_create_trip_missing_is_private_return_422(auth_client):
    payload = {
        "latitude": 48.8566,
        "longitude": 2.3522,
        "title": "Trip to Paris",
        "description": "A wonderful trip to the city of lights.",
        "addresses": ["Paris, France"],
        "start_date": "2026-09-01",
        "end_date": "2026-09-05",
    }
    response = await auth_client.post("/trips", json=payload)
    assert response.status_code == 422


async def test_create_trip_not_authenticated_return_401(client):
    payload = {
        "latitude": 48.8566,
        "longitude": 2.3522,
        "title": "Trip to Paris",
        "description": "A wonderful trip to the city of lights.",
        "addresses": ["Paris, France"],
        "start_date": "2026-09-01",
        "end_date": "2026-09-05",
        "is_private": False,
    }
    response = await client.post("/trips", json=payload)
    assert response.status_code == 401


# update trip by id ###################################################################


async def test_update_trip_return_200(auth_client):
    trip = await TripFactory.create_async(user_id=FIXED_MOCKED_USER_ID)
    response = await auth_client.patch(
        f"/trips/{trip.uuid}", json={"title": "new title"}
    )
    assert response.status_code == 200
    response = response.json()
    assert response["uuid"] == str(trip.uuid)
    assert response["title"] == "new title"
    assert response["is_owner"] is True


async def test_update_trip_not_found_return_404(auth_client):
    response = await auth_client.patch(
        f"/trips/{uuid.uuid4()}", json={"title": "new title"}
    )
    assert response.status_code == 404


async def test_update_trip_not_authenticated_return_401(client):
    trip = await TripFactory.create_async()
    response = await client.patch(f"/trips/{trip.uuid}", json={"title": "new title"})
    assert response.status_code == 401


async def test_update_not_my_trip_return_403(auth_client):
    trip = await TripFactory.create_async()  # user_id will be different
    response = await auth_client.patch(
        f"/trips/{trip.uuid}", json={"title": "new title"}
    )
    assert response.status_code == 403


# delete trip #########################################################################


async def test_delete_my_trip_return_204(auth_client):
    trip = await TripFactory.create_async(user_id=FIXED_MOCKED_USER_ID)
    response = await auth_client.delete(f"/trips/{trip.uuid}")
    assert response.status_code == 204


async def test_delete_trip_not_found_return_404(auth_client):
    response = await auth_client.delete(f"/trips/{uuid.uuid4()}")
    assert response.status_code == 404


async def test_delete_trip_not_authenticated_return_401(client):
    trip = await TripFactory.create_async()
    response = await client.delete(f"/trips/{trip.uuid}")
    assert response.status_code == 401


async def test_delete_not_my_trip_return_403(auth_client):
    trip = await TripFactory.create_async()  # user_id will be different
    response = await auth_client.delete(f"/trips/{trip.uuid}")
    assert response.status_code == 403
