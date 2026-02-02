"""JWT utilities for auth (Phase 2)."""

import re
from datetime import datetime, timezone, timedelta
from typing import Optional

from jose import JWTError, jwt
from config.settings import settings
import logging

logger = logging.getLogger(__name__)


def create_access_token(sub: str, expires_delta: Optional[timedelta] = None) -> dict:
    """Create a JWT access token. sub is user_id or session_id (string)."""
    if expires_delta is None:
        expires_delta = timedelta(days=settings.jwt_access_token_expire_days)
    expire = datetime.now(timezone.utc) + expires_delta
    to_encode = {
        "sub": str(sub),
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    encoded = jwt.encode(
        to_encode,
        settings.jwt_secret_key,
        algorithm=settings.jwt_algorithm,
    )
    return {"access_token": encoded, "token_type": "bearer", "expires_at": expire}


def verify_token(token: str) -> Optional[str]:
    """Verify JWT and return sub (user_id or session_id)."""
    if not token or not isinstance(token, str):
        return None
    if not re.match(r"^[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+$", token):
        return None
    try:
        payload = jwt.decode(
            token,
            settings.jwt_secret_key,
            algorithms=[settings.jwt_algorithm],
        )
        return payload.get("sub")
    except JWTError:
        return None
