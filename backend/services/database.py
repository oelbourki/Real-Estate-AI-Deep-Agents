"""Database service for User and Session (Auth Phase 2). Uses same Postgres as checkpointer when configured."""

import logging
from typing import List, Optional

from config.settings import settings
from sqlmodel import Session as SQLModelSession, SQLModel, create_engine, select
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import SQLAlchemyError

from models.user import User
from models.session import Session as ChatSession

logger = logging.getLogger(__name__)


def _get_connection_url() -> str:
    """Build Postgres URL from settings (same as checkpointer)."""
    from urllib.parse import quote_plus

    user = quote_plus(settings.postgres_user)
    password = quote_plus(settings.postgres_password or "")
    return f"postgresql://{user}:{password}@{settings.postgres_host}:{settings.postgres_port}/{settings.postgres_db}"


class DatabaseService:
    """Sync database service for User and Session. Uses same Postgres as checkpointer."""

    def __init__(self):
        self._engine = None

    @property
    def engine(self):
        if self._engine is not None:
            return self._engine
        if not (
            settings.postgres_host and settings.postgres_db and settings.postgres_user
        ):
            return None
        try:
            url = _get_connection_url()
            self._engine = create_engine(
                url,
                pool_pre_ping=True,
                poolclass=QueuePool,
                pool_size=min(3, settings.postgres_pool_size),
                max_overflow=2,
            )
            SQLModel.metadata.create_all(self._engine)
            logger.info("Auth DB (User/Session) initialized")
            return self._engine
        except SQLAlchemyError as e:
            logger.warning("Auth DB init failed: %s", e)
            return None

    def _session(self) -> SQLModelSession:
        if self.engine is None:
            raise RuntimeError(
                "PostgreSQL not configured for auth. Set POSTGRES_* env vars."
            )
        return SQLModelSession(self.engine)

    def create_user(self, email: str, hashed_password: str) -> User:
        with self._session() as session:
            user = User(email=email, hashed_password=hashed_password)
            session.add(user)
            session.commit()
            session.refresh(user)
            return user

    def get_user(self, user_id: int) -> Optional[User]:
        if self.engine is None:
            return None
        with self._session() as session:
            return session.get(User, user_id)

    def get_user_by_email(self, email: str) -> Optional[User]:
        if self.engine is None:
            return None
        with self._session() as session:
            return session.exec(select(User).where(User.email == email)).first()

    def create_session(
        self, session_id: str, user_id: int, name: str = ""
    ) -> ChatSession:
        with self._session() as session:
            s = ChatSession(id=session_id, user_id=user_id, name=name)
            session.add(s)
            session.commit()
            session.refresh(s)
            return s

    def get_session(self, session_id: str) -> Optional[ChatSession]:
        if self.engine is None:
            return None
        with self._session() as session:
            return session.get(ChatSession, session_id)

    def get_user_sessions(self, user_id: int) -> List[ChatSession]:
        if self.engine is None:
            return []
        with self._session() as session:
            return list(
                session.exec(
                    select(ChatSession)
                    .where(ChatSession.user_id == user_id)
                    .order_by(ChatSession.created_at)
                ).all()
            )

    def update_session_name(self, session_id: str, name: str) -> Optional[ChatSession]:
        with self._session() as session:
            s = session.get(ChatSession, session_id)
            if not s:
                return None
            s.name = name
            session.add(s)
            session.commit()
            session.refresh(s)
            return s

    def delete_session(self, session_id: str) -> bool:
        with self._session() as session:
            s = session.get(ChatSession, session_id)
            if not s:
                return False
            session.delete(s)
            session.commit()
            return True


database_service = DatabaseService()
