from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Response, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import CurrentUser, current_user
from app.core.security import (
    SESSION_COOKIE,
    TOKEN_TTL_HOURS,
    create_session_token,
    verify_password,
)
from app.db import models
from app.db.postgres import get_session

router = APIRouter(prefix="/api/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: str
    username: str
    role: str
    display_name: str
    display_name_si: str | None = None
    locale: str
    school_id: str | None = None
    school_name: str | None = None
    student_id: str | None = None
    teacher_id: str | None = None
    role_title: str | None = None
    #: Where the frontend should land this user.
    home_path: str


def _home_path(role: str) -> str:
    return "/student" if role == "student" else "/teacher"


def _user_response(session: Session, user: models.User) -> UserResponse:
    school = session.get(models.School, user.school_id) if user.school_id else None
    teacher = session.get(models.Teacher, user.teacher_id) if user.teacher_id else None
    return UserResponse(
        id=user.id,
        username=user.username,
        role=user.role,
        display_name=user.display_name,
        display_name_si=user.display_name_si,
        locale=user.locale,
        school_id=user.school_id,
        school_name=school.name if school else None,
        student_id=user.student_id,
        teacher_id=user.teacher_id,
        role_title=teacher.role_title if teacher else None,
        home_path=_home_path(user.role),
    )


@router.post("/login", response_model=UserResponse)
def login(
    payload: LoginRequest,
    response: Response,
    session: Session = Depends(get_session),
) -> UserResponse:
    user = (
        session.execute(
            select(models.User).where(models.User.username == payload.username)
        )
        .scalars()
        .first()
    )
    # Same message and same work either way, so the response cannot be used to
    # enumerate usernames.
    if user is None or not user.is_active or not verify_password(
        payload.password, user.password_hash
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password.",
        )

    token = create_session_token(
        user_id=user.id,
        username=user.username,
        role=user.role,
        student_id=user.student_id,
        teacher_id=user.teacher_id,
        school_id=user.school_id,
    )
    response.set_cookie(
        SESSION_COOKIE,
        token,
        httponly=True,
        samesite="lax",
        secure=False,  # local http development; set True behind TLS
        max_age=TOKEN_TTL_HOURS * 3600,
        path="/",
    )
    return _user_response(session, user)


class DemoAccount(BaseModel):
    role: str
    username: str
    display_name: str
    role_title: str | None = None
    school_name: str | None = None


@router.get("/demo-accounts", response_model=list[DemoAccount])
def demo_accounts(session: Session = Depends(get_session)) -> list[DemoAccount]:
    """One sign-in per role, for the demonstration login screen.

    Read from the database rather than hardcoded, because seeded names shift whenever
    the generator changes and a stale example on the login page is worse than none.
    Returns nothing when demo mode is off.
    """
    if not settings.demo_mode:
        return []

    accounts: list[DemoAccount] = []
    for role in ("admin", "counsellor", "teacher", "student"):
        user = (
            session.execute(
                select(models.User)
                .where(models.User.role == role, models.User.is_active.is_(True))
                .order_by(models.User.id)
                .limit(1)
            )
            .scalars()
            .first()
        )
        if user is None:
            continue
        school = session.get(models.School, user.school_id) if user.school_id else None
        teacher = session.get(models.Teacher, user.teacher_id) if user.teacher_id else None
        accounts.append(
            DemoAccount(
                role=role,
                username=user.username,
                display_name=user.display_name,
                role_title=teacher.role_title if teacher else "Learner",
                school_name=school.name if school else None,
            )
        )
    return accounts


@router.post("/logout")
def logout(response: Response) -> dict:
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"status": "signed_out"}


@router.get("/me", response_model=UserResponse)
def me(
    user: CurrentUser = Depends(current_user),
    session: Session = Depends(get_session),
) -> UserResponse:
    record = session.get(models.User, user.id)
    if record is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Sign in to continue.")
    return _user_response(session, record)
