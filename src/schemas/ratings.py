from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class Rating(BaseModel):
    rating: int = Field(ge=1, le=5)
    comment: str = Field(min_length=1, max_length=2000)


class RatingRead(BaseModel):
    user_id: UUID
    user_name: str
    rating: int
    comment: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ListRatings(BaseModel):
    ratings: list[RatingRead]
    total: int  # total ratings for the trip, independent of skip/limit
