"""Auth routes and dependencies (Phase 2): register, login, session CRUD, JWT verification."""

import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel

from config.settings import settings
from api.schemas import (
    UserCreate,
    UserResponse,
    TokenResponse,
    SessionResponse,
)
from services.database import database_service
from utils.auth_jwt import create_access_token, verify_token
from models.user import User
from models.session import Session as ChatSession
import logging

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/auth", tags=["auth"])
security = HTTPBearer(auto_error=False)


def _auth_required() -> bool:
    """True if Postgres is configured so we can use auth DB."""
    return bool(
        settings.postgres_host and settings.postgres_db and settings.postgres_user
    )


async def get_current_user_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[User]:
    """Return current user if valid JWT (user token) is provided; else None."""
    if not _auth_required() or not credentials:
        return None
    sub = verify_token(credentials.credentials)
    if not sub:
        return None
    try:
        user_id = int(sub)
    except ValueError:
        return None
    user = database_service.get_user(user_id)
    return user


async def get_current_session_optional(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> Optional[ChatSession]:
    """Return current session if valid JWT (session token) is provided; else None."""
    if not _auth_required() or not credentials:
        return None
    sub = verify_token(credentials.credentials)
    if not sub:
        return None
    return database_service.get_session(sub)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> User:
    """Require valid JWT and return current user."""
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing authorization")
    sub = verify_token(credentials.credentials)
    if not sub:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    try:
        user_id = int(sub)
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token")
    user = database_service.get_user(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


async def get_current_session(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> ChatSession:
    """Require valid JWT and return current session."""
    if not credentials:
        raise HTTPException(status_code=401, detail="Missing authorization")
    sub = verify_token(credentials.credentials)
    if not sub:
        raise HTTPException(status_code=401, detail="Invalid or expired token")
    session = database_service.get_session(sub)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    return session


@router.post("/register", response_model=UserResponse)
async def register(data: UserCreate):
    """Register a new user. Requires Postgres (auth DB)."""
    if not _auth_required():
        raise HTTPException(
            status_code=503,
            detail="Auth requires PostgreSQL. Set POSTGRES_* env vars.",
        )
    if database_service.get_user_by_email(data.email):
        raise HTTPException(status_code=400, detail="Email already registered")
    user = database_service.create_user(
        email=data.email,
        hashed_password=User.hash_password(data.password.get_secret_value()),
    )
    token = create_access_token(str(user.id))
    return UserResponse(
        id=user.id,
        email=user.email,
        token=TokenResponse(
            access_token=token["access_token"],
            token_type=token["token_type"],
            expires_at=token["expires_at"],
        ),
    )


class LoginForm(BaseModel):
    """Login form (username=email, password)."""

    username: str  # email
    password: str
    grant_type: str = "password"


@router.post("/login", response_model=TokenResponse)
async def login(form: LoginForm):
    """Login with email and password. Returns JWT (sub=user_id)."""
    if not _auth_required():
        raise HTTPException(status_code=503, detail="Auth requires PostgreSQL.")
    user = database_service.get_user_by_email(form.username.strip())
    if not user or not user.verify_password(form.password):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    token = create_access_token(str(user.id))
    return TokenResponse(
        access_token=token["access_token"],
        token_type=token["token_type"],
        expires_at=token["expires_at"],
    )


@router.post("/session", response_model=SessionResponse)
async def create_session(user: User = Depends(get_current_user)):
    """Create a new chat session for the current user. Returns session_id and JWT (sub=session_id)."""
    session_id = str(uuid.uuid4())
    s = database_service.create_session(session_id, user.id)
    token = create_access_token(session_id)
    return SessionResponse(
        session_id=s.id,
        name=s.name,
        token=TokenResponse(
            access_token=token["access_token"],
            token_type=token["token_type"],
            expires_at=token["expires_at"],
        ),
    )


@router.get("/sessions", response_model=List[SessionResponse])
async def list_sessions(user: User = Depends(get_current_user)):
    """List chat sessions for the current user."""
    sessions = database_service.get_user_sessions(user.id)
    return [
        SessionResponse(
            session_id=s.id,
            name=s.name,
            token=TokenResponse(**create_access_token(s.id)),
        )
        for s in sessions
    ]


class SessionNameUpdate(BaseModel):
    name: str = ""


@router.patch("/session/{session_id}/name", response_model=SessionResponse)
async def update_session_name(
    session_id: str,
    body: SessionNameUpdate,
    current: ChatSession = Depends(get_current_session),
):
    """Update session name. Only the session owner can update."""
    if current.id != session_id:
        raise HTTPException(status_code=403, detail="Cannot update another session")
    s = database_service.update_session_name(session_id, (body.name or "")[:100])
    if not s:
        raise HTTPException(status_code=404, detail="Session not found")
    token = create_access_token(s.id)
    return SessionResponse(
        session_id=s.id,
        name=s.name,
        token=TokenResponse(
            access_token=token["access_token"],
            token_type=token["token_type"],
            expires_at=token["expires_at"],
        ),
    )


@router.delete("/session/{session_id}")
async def delete_session(
    session_id: str,
    current: ChatSession = Depends(get_current_session),
):
    """Delete a session. Only the session owner can delete."""
    if current.id != session_id:
        raise HTTPException(status_code=403, detail="Cannot delete another session")
    if not database_service.delete_session(session_id):
        raise HTTPException(status_code=404, detail="Session not found")
    return {"message": "Session deleted"}
