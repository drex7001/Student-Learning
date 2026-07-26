"""Request-scoped identity and authorisation.

Access rules live here rather than in the UI, because a hidden button is not a control.
The rule that matters most: a student may read their own learning data and nothing
else, and no student may reach the risk endpoints at all.
"""

from __future__ import annotations

from dataclasses import dataclass

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.security import SESSION_COOKIE, decode_session_token
from app.db import models
from app.db.postgres import get_session

STAFF_ROLES = frozenset({"teacher", "counsellor", "admin"})


@dataclass(frozen=True)
class CurrentUser:
    id: str
    username: str
    role: str
    display_name: str
    student_id: str | None
    teacher_id: str | None
    school_id: str | None

    @property
    def is_staff(self) -> bool:
        return self.role in STAFF_ROLES


def _unauthorised() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED, detail="Sign in to continue."
    )


def current_user(
    request: Request, session: Session = Depends(get_session)
) -> CurrentUser:
    token = request.cookies.get(SESSION_COOKIE)
    if not token:
        raise _unauthorised()
    claims = decode_session_token(token)
    if claims is None:
        raise _unauthorised()

    user = session.get(models.User, claims.get("sub"))
    if user is None or not user.is_active:
        raise _unauthorised()

    return CurrentUser(
        id=user.id,
        username=user.username,
        role=user.role,
        display_name=user.display_name,
        student_id=user.student_id,
        teacher_id=user.teacher_id,
        school_id=user.school_id,
    )


def optional_user(
    request: Request, session: Session = Depends(get_session)
) -> CurrentUser | None:
    try:
        return current_user(request, session)
    except HTTPException:
        return None


def require_role(*roles: str):
    allowed = frozenset(roles)

    def dependency(user: CurrentUser = Depends(current_user)) -> CurrentUser:
        if user.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Your role does not have access to this area.",
            )
        return user

    return dependency


require_staff = require_role("teacher", "counsellor", "admin")
require_admin = require_role("admin")


def require_admin_or_bootstrap(
    request: Request, session: Session = Depends(get_session)
) -> CurrentUser | None:
    """Administrator-only, except on a database that has no accounts yet.

    The seeding endpoints create the first administrator, so requiring an
    administrator to call them would be a deadlock. The exception is narrow and
    self-closing: it applies only while `users` is empty, which stops being true the
    moment the first seed completes.
    """
    if session.query(models.User).limit(1).count() == 0:
        return None
    user = current_user(request, session)
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Seeding and imports are restricted to administrators.",
        )
    return user


def authorise_student_access(user: CurrentUser, student_id: str) -> None:
    """Staff may read any learner in the system; a student may read only themselves.

    Enforced at the data boundary so changing a URL cannot reveal another child.
    """
    if user.is_staff:
        return
    if user.role == "student" and user.student_id == student_id:
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="You can only view your own learning record.",
    )


def deny_students(user: CurrentUser) -> None:
    """Disengagement risk is never shown to the student it describes.

    A flag must cost the student nothing if it was wrong; telling a child a model
    thinks they will leave school is a cost. See research/dropout-ews/REPORT.md 11.1.
    """
    if user.role == "student":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Risk information is available to teachers and counsellors only.",
        )
