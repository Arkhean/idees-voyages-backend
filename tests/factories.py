import uuid as uuid_import
from datetime import UTC, datetime

import factory

from src.database.models import Rating, Trip, User

from .conftest import TestingAsyncSessionLocal


class AsyncFactory(factory.Factory):
    @classmethod
    async def create_async(cls, **kwargs):
        instance = cls.build(**kwargs)
        async with TestingAsyncSessionLocal() as session:
            session.add(instance)
            await session.commit()
            await session.refresh(instance)
        return instance


async def _ensure_persisted_user_id(kwargs: dict) -> dict:
    """Fill in `user_id` with a freshly persisted user's id, unless already given.

    `Trip.user_id`/`Rating.user_id` are foreign keys to `user.id`, enforced
    by every real database (and locally too, since SQLite has the
    `PRAGMA foreign_keys=ON` pragma enabled for tests). A random UUID would
    fail that constraint, so tests that don't care which user owns a trip or
    left a rating still need a real, persisted one.
    """
    if "user_id" not in kwargs:
        user = await UserFactory.create_async()
        kwargs["user_id"] = user.id
    return kwargs


class TripFactory(AsyncFactory):
    class Meta:
        model = Trip

    id = factory.Sequence(lambda n: n + 1)
    uuid = factory.LazyFunction(uuid_import.uuid4)
    latitude = factory.Faker("latitude")
    longitude = factory.Faker("longitude")
    title = factory.Faker("text", max_nb_chars=50)
    description = factory.Faker("paragraph")

    created_at = factory.LazyFunction(lambda: datetime.now(UTC))
    updated_at = factory.LazyFunction(lambda: datetime.now(UTC))

    addresses = factory.LazyFunction(
        lambda: ["123 Rue de Paris, Paris", "456 Avenue Victor Hugo, Lyon"]
    )
    start_date = factory.Faker("date_object")
    end_date = factory.Faker("date_object")

    @classmethod
    async def create_async(cls, **kwargs):
        """Create a Trip, persisting a real owner first if `user_id` wasn't given."""
        return await super().create_async(**await _ensure_persisted_user_id(kwargs))


class UserFactory(AsyncFactory):
    class Meta:
        model = User

    id = factory.LazyFunction(uuid_import.uuid4)
    email = factory.Faker("email")
    name = factory.Faker("name")
    hashed_password = "hashed_dummy_password"
    is_active = True
    is_superuser = False
    is_verified = True


class RatingFactory(AsyncFactory):
    class Meta:
        model = Rating

    trip_id = factory.Sequence(lambda n: n + 1)
    rating = factory.Faker("random_int", min=1, max=5)
    comment = factory.Faker("sentence")

    created_at = factory.LazyFunction(lambda: datetime.now(UTC))
    updated_at = factory.LazyFunction(lambda: datetime.now(UTC))

    @classmethod
    async def create_async(cls, **kwargs):
        """Create a Rating, persisting a real rater first if `user_id` wasn't given."""
        return await super().create_async(**await _ensure_persisted_user_id(kwargs))
