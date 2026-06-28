from __future__ import annotations

import time

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.config import settings
from app.db import models  # noqa: F401
from app.db.postgres import Base, engine
from app.routers.diagnosis import router as diagnosis_router
from app.routers.internal import router as internal_router
from app.routers.learning import router as learning_router
from app.routers.student_support import router as student_support_router


app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def wait_for_postgres(max_attempts: int = 20, delay_seconds: float = 2.0) -> None:
    last_error: Exception | None = None
    for _ in range(max_attempts):
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
            return
        except Exception as exc:  # pragma: no cover - exercised in container startup
            last_error = exc
            time.sleep(delay_seconds)
    if last_error is not None:
        raise last_error


@app.on_event("startup")
def startup() -> None:
    wait_for_postgres()
    Base.metadata.create_all(bind=engine)


@app.get("/health")
def healthcheck() -> dict:
    return {"status": "ok"}


app.include_router(internal_router)
app.include_router(diagnosis_router)
app.include_router(learning_router)
app.include_router(student_support_router)
