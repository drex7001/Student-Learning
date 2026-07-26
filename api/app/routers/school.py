from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.core.deps import CurrentUser, require_staff
from app.db.postgres import get_session
from app.repositories.postgres_repository import PostgresRepository

router = APIRouter(prefix="/api/school", tags=["school"])


@router.get("/schools")
def list_schools(
    user: CurrentUser = Depends(require_staff),
    session: Session = Depends(get_session),
) -> list[dict]:
    return PostgresRepository(session).list_schools()


@router.get("/classes")
def list_classes(
    school_id: str | None = Query(default=None),
    user: CurrentUser = Depends(require_staff),
    session: Session = Depends(get_session),
) -> list[dict]:
    return PostgresRepository(session).list_classes(school_id=school_id or user.school_id)
