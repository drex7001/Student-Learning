"""Password hashing and session tokens.

Uses ``bcrypt`` directly rather than through passlib: one less layer, and passlib 1.7.4
emits a spurious ``bcrypt.__about__`` warning against bcrypt 4.x.

The token is carried in an httpOnly, SameSite=Lax cookie rather than a header, so it is
never reachable from JavaScript. The frontend calls the API same-origin through a
Next.js rewrite, which keeps the cookie first-party.
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone
from typing import Any

import bcrypt
import jwt

ALGORITHM = "HS256"
SESSION_COOKIE = "wellbeing_session"
TOKEN_TTL_HOURS = 12

# A generated fallback keeps a fresh checkout working, but every session is then
# invalidated on restart. Set JWT_SECRET in any environment that matters.
JWT_SECRET: str = os.getenv("JWT_SECRET", "") or os.urandom(32).hex()


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def create_session_token(
    *,
    user_id: str,
    username: str,
    role: str,
    student_id: str | None = None,
    teacher_id: str | None = None,
    school_id: str | None = None,
) -> str:
    now = datetime.now(tz=timezone.utc)
    payload: dict[str, Any] = {
        "sub": user_id,
        "username": username,
        "role": role,
        "student_id": student_id,
        "teacher_id": teacher_id,
        "school_id": school_id,
        "iat": now,
        "exp": now + timedelta(hours=TOKEN_TTL_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=ALGORITHM)


def decode_session_token(token: str) -> dict[str, Any] | None:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
    except jwt.PyJWTError:
        return None
