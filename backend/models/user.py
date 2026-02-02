"""User model for auth (Phase 2)."""

from typing import TYPE_CHECKING, List

from passlib.context import CryptContext
from sqlmodel import Field, Relationship

from models.base import BaseModel

if TYPE_CHECKING:
    from models.session import Session

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


class User(BaseModel, table=True):
    """User model for storing user accounts."""

    __tablename__ = "user"

    id: int | None = Field(default=None, primary_key=True)
    email: str = Field(unique=True, index=True)
    hashed_password: str = Field()
    sessions: List["Session"] = Relationship(back_populates="user")

    def verify_password(self, password: str) -> bool:
        """Verify if the provided password matches the hash."""
        return pwd_context.verify(password, self.hashed_password)

    @staticmethod
    def hash_password(password: str) -> str:
        """Hash a password using bcrypt."""
        return pwd_context.hash(password)
