"""Session model for chat sessions (Auth Phase 2)."""

from typing import TYPE_CHECKING

from sqlmodel import Field, Relationship

from models.base import BaseModel

if TYPE_CHECKING:
    from models.user import User


class Session(BaseModel, table=True):
    """Session model for storing chat sessions (one per thread)."""

    __tablename__ = "session"

    id: str = Field(primary_key=True)
    user_id: int = Field(foreign_key="user.id")
    name: str = Field(default="", max_length=255)
    user: "User" = Relationship(back_populates="sessions")
