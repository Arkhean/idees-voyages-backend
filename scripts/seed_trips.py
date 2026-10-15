"""Seed the app database with sample trips (and ratings) across France, for local dev/demo use.

Usage (from idees-voyages-backend/, run as a module so `src` is importable):
    uv run alembic upgrade head
    uv run python -m scripts.seed_trips [--count 100]

The schema itself is managed by Alembic, not by this script, so run
migrations first — this script only seeds data into an already-migrated
database.

Connects to whatever DATABASE_URL is configured (via .env / environment),
i.e. the real app database — not the test database used by the test suite.
Trips are assigned to a small pool of demo user accounts (created if they
don't already exist) so ownership, "only my trips", and private-trip
behavior are all testable by logging in as one of them. Each public trip
also gets a random handful of ratings from the other demo users, matching
the app's rules: nobody can rate their own trip, and private trips get no
ratings since nobody but the owner can see them.
"""

import argparse
import asyncio
import random
import uuid
from datetime import UTC, datetime, timedelta

from faker import Faker
from fastapi_users.password import PasswordHelper
from sqlalchemy import inspect, select

from src.database.database import SessionLocal, engine
from src.database.models import Rating, Trip, User

fake = Faker("fr_FR")
password_helper = PasswordHelper()

DEMO_PASSWORD = "password123"
DEMO_USERS = [
    {"email": "alice@example.com", "name": "Alice Martin"},
    {"email": "bob@example.com", "name": "Bob Dupont"},
    {"email": "chloe@example.com", "name": "Chloé Bernard"},
    {"email": "david@example.com", "name": "David Rousseau"},
    {"email": "emma@example.com", "name": "Emma Lefevre"},
]

# Real French cities to scatter trips around, so coordinates land somewhere
# sensible instead of at random points in the sea or across a border.
FRENCH_CITIES = [
    ("Paris", 48.8566, 2.3522),
    ("Lyon", 45.7640, 4.8357),
    ("Marseille", 43.2965, 5.3698),
    ("Toulouse", 43.6047, 1.4442),
    ("Nice", 43.7102, 7.2620),
    ("Nantes", 47.2184, -1.5536),
    ("Strasbourg", 48.5734, 7.7521),
    ("Montpellier", 43.6108, 3.8767),
    ("Bordeaux", 44.8378, -0.5792),
    ("Lille", 50.6292, 3.0573),
    ("Rennes", 48.1173, -1.6778),
    ("Reims", 49.2583, 4.0317),
    ("Le Havre", 49.4944, 0.1079),
    ("Saint-Étienne", 45.4397, 4.3872),
    ("Toulon", 43.1242, 5.9280),
    ("Grenoble", 45.1885, 5.7245),
    ("Dijon", 47.3220, 5.0415),
    ("Angers", 47.4784, -0.5632),
    ("Nîmes", 43.8367, 4.3601),
    ("Annecy", 45.8992, 6.1294),
]

TRIP_THEMES = [
    "Weekend getaway",
    "City break",
    "Family holiday",
    "Road trip",
    "Food & wine tour",
    "Cultural escape",
    "Hiking adventure",
    "Beach retreat",
    "Romantic trip",
    "Solo adventure",
]

# Coordinate jitter in degrees (~a few km) so trips cluster near, but don't
# all land exactly on, each city center.
JITTER_DEGREES = 0.1

REVIEW_COMMENTS = [
    "Amazing experience, highly recommend!",
    "Had a wonderful time, would go again.",
    "Beautiful scenery and great food.",
    "A bit crowded but still enjoyable.",
    "Perfect weekend getaway.",
    "Loved every moment of this trip.",
    "Great value for the price.",
    "Could have been better organized, but still fun.",
    "Breathtaking views, unforgettable memories.",
    "Exactly what I needed for a relaxing break.",
]

# Every demo user besides the trip's owner is a candidate rater, so this is
# effectively capped at len(DEMO_USERS) - 1 regardless of the value here.
MAX_RATERS_PER_TRIP = 4


async def get_or_create_demo_users(db) -> list[User]:
    """Fetch the demo users, creating any that don't exist yet."""
    users = []
    for demo in DEMO_USERS:
        result = await db.execute(select(User).where(User.email == demo["email"]))
        user = result.scalar_one_or_none()
        if user is None:
            user = User(
                id=uuid.uuid4(),
                email=demo["email"],
                name=demo["name"],
                hashed_password=password_helper.hash(DEMO_PASSWORD),
                is_active=True,
                is_superuser=False,
                is_verified=True,
            )
            db.add(user)
            print(f"Created demo user {demo['email']} (password: {DEMO_PASSWORD})")
        users.append(user)
    await db.commit()
    for user in users:
        await db.refresh(user)
    return users


def random_trip(users: list[User]) -> Trip:
    """Build one unsaved Trip near a random French city, owned by a random demo user."""
    city_name, city_lat, city_lng = random.choice(FRENCH_CITIES)
    theme = random.choice(TRIP_THEMES)
    start_date = datetime.now(UTC).date() + timedelta(days=random.randint(-60, 300))
    end_date = start_date + timedelta(days=random.randint(1, 14))

    return Trip(
        uuid=uuid.uuid4(),
        latitude=city_lat + random.uniform(-JITTER_DEGREES, JITTER_DEGREES),
        longitude=city_lng + random.uniform(-JITTER_DEGREES, JITTER_DEGREES),
        title=f"{theme} in {city_name}"[:50],
        description=fake.paragraph(nb_sentences=5),
        addresses=[f"{fake.street_address()}, {city_name}, France"],
        start_date=start_date,
        end_date=end_date,
        is_private=random.random() < 0.1,  # ~10% private
        user_id=random.choice(users).id,
    )


def random_ratings_for_trip(trip: Trip, users: list[User]) -> list[Rating]:
    """Build 0-4 unsaved Ratings for a trip, from demo users other than its owner.

    Skips private trips entirely: nobody but the owner can even see one, and
    the owner can't rate their own trip, so a private trip has no one able
    to leave a rating.
    """
    if trip.is_private:
        return []

    possible_raters = [user for user in users if user.id != trip.user_id]
    raters = random.sample(
        possible_raters, k=random.randint(0, min(MAX_RATERS_PER_TRIP, len(possible_raters)))
    )

    return [
        Rating(
            trip_id=trip.id,
            user_id=rater.id,
            rating=random.randint(1, 5),
            comment=random.choice(REVIEW_COMMENTS),
        )
        for rater in raters
    ]


async def _ensure_schema_is_migrated() -> None:
    """Fail fast with a clear message if migrations haven't been applied yet."""
    async with engine.connect() as conn:
        table_names = await conn.run_sync(lambda sync_conn: inspect(sync_conn).get_table_names())
    if "trips" not in table_names:
        raise SystemExit(
            "The database has no 'trips' table yet. Run `uv run alembic upgrade head` "
            "before seeding."
        )


async def seed(count: int) -> None:
    """Create the demo users (if needed) and insert `count` random French trips with ratings."""
    await _ensure_schema_is_migrated()

    async with SessionLocal() as db:
        users = await get_or_create_demo_users(db)

        trips = [random_trip(users) for _ in range(count)]
        db.add_all(trips)
        await db.flush()  # assigns trip.id for each, without expiring attributes like commit does

        ratings = [rating for trip in trips for rating in random_ratings_for_trip(trip, users)]
        db.add_all(ratings)

        await db.commit()

    print(
        f"Seeded {count} trips ({len(ratings)} ratings) across {len(users)} demo users "
        "(all in France)."
    )


def main() -> None:
    """Parse CLI args and run the seeding."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--count", type=int, default=100, help="Number of trips to create (default: 100)."
    )
    args = parser.parse_args()
    asyncio.run(seed(args.count))


if __name__ == "__main__":
    main()
