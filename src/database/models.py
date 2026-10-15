import uuid as uuid_import  # to not mix with the uuid field in the Trip model
from datetime import date, datetime

from fastapi_users_db_sqlalchemy import SQLAlchemyBaseUserTableUUID
from fastapi_users_db_sqlalchemy.generics import GUID
from sqlalchemy import (
    JSON,
    UUID,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from .database import Base

# --------------------------------------------
# Trips
# --------------------------------------------


class Trip(Base):
    __tablename__ = "trips"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    uuid: Mapped[UUID] = mapped_column(UUID, nullable=False, unique=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    title: Mapped[str] = mapped_column(String(50), nullable=False)
    description: Mapped[str] = mapped_column(String(2000), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    addresses: Mapped[list[str]] = mapped_column(JSON, default=list)
    start_date: Mapped[date | None] = mapped_column(Date, nullable=False)
    end_date: Mapped[date | None] = mapped_column(Date, nullable=False)

    # GUID (not the plain UUID type above) to match `User.id`'s storage
    # format: fastapi-users encodes UUIDs differently than SQLAlchemy's
    # native UUID type, so a foreign key needs the same column type to
    # actually match rows (a SQL-level comparison, not a Python one).
    user_id: Mapped[uuid_import.UUID] = mapped_column(
        GUID, ForeignKey("user.id"), nullable=False
    )
    is_private: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)


class Rating(Base):
    __tablename__ = "ratings"

    # only one rating by user on each trip, so the primary key is (trip_id, user_id)

    trip_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("trips.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[uuid_import.UUID] = mapped_column(
        GUID, ForeignKey("user.id"), nullable=False, primary_key=True
    )

    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    comment: Mapped[str] = mapped_column(String(2000), nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )


# --------------------------------------------
# Users authentication
# --------------------------------------------


class User(SQLAlchemyBaseUserTableUUID, Base):
    name: Mapped[str] = mapped_column(String(100), nullable=False)
