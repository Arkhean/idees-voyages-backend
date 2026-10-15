from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class TripBase(BaseModel):
    latitude: float
    longitude: float
    title: str = Field(..., max_length=50, description="Max 50 characters")
    description: str = Field(..., max_length=2000, description="Max 2000 characters")
    addresses: list[str] = []
    start_date: date
    end_date: date
    is_private: bool


class TripCreate(TripBase):
    pass


class TripUpdate(BaseModel):
    title: str | None = Field(None, max_length=50)
    description: str | None = Field(None, max_length=2000)
    latitude: float | None = None
    longitude: float | None = None
    addresses: list[str] | None = None
    start_date: date | None = None
    end_date: date | None = None
    is_private: bool | None = None


class Trip(TripBase):
    uuid: UUID
    created_at: datetime
    updated_at: datetime
    mean_rating: float
    rating_people_number: int
    is_owner: bool  # whether the requesting (optional) user owns this trip

    model_config = ConfigDict(from_attributes=True)


class ListTrips(BaseModel):
    trips: list[Trip]
    total: int  # total trips matching the filters, independent of skip/limit
