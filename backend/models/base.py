"""Base model with created_at."""

from datetime import datetime, timezone

from sqlmodel import Field, SQLModel


class BaseModel(SQLModel):
    """Base model with common fields."""

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
