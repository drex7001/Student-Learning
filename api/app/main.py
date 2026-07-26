from __future__ import annotations

import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text

from app.core.config import settings
from app.db import models  # noqa: F401
from app.db.postgres import Base, engine
from app.risk import dropout_ews_bn as bn
from app.routers.auth import router as auth_router
from app.routers.diagnosis import router as diagnosis_router
from app.routers.graph import router as graph_router
from app.routers.internal import router as internal_router
from app.routers.learning import router as learning_router
from app.routers.risk import router as risk_router
from app.routers.school import router as school_router
from app.routers.student_support import router as student_support_router

logger = logging.getLogger(__name__)


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


@asynccontextmanager
async def lifespan(app: FastAPI):
    wait_for_postgres()
    Base.metadata.create_all(bind=engine)

    # Build the risk network once. RiskModel is a frozen dataclass holding a pgmpy
    # model plus its VariableElimination engine, so it is safe to share across
    # requests (REPORT.md section 4). Rebuilding it per request would cost ~200ms.
    variant = bn.ModelVariant(settings.risk_model_variant)
    risk_model = bn.build_model(variant)
    app.state.risk_model = risk_model
    logger.info(
        "risk model ready: variant=%s fingerprint=%s nodes=%d",
        risk_model.variant.value,
        risk_model.fingerprint,
        len(risk_model.nodes),
    )

    yield

    app.state.risk_model = None


app = FastAPI(title=settings.app_name, lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_origins),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def healthcheck() -> dict:
    risk_model = getattr(app.state, "risk_model", None)
    return {
        "status": "ok",
        "risk_model": {
            "variant": risk_model.variant.value,
            "fingerprint": risk_model.fingerprint,
        }
        if risk_model is not None
        else None,
    }


app.include_router(auth_router)
app.include_router(internal_router)
app.include_router(risk_router)
app.include_router(graph_router)
app.include_router(school_router)
app.include_router(diagnosis_router)
app.include_router(learning_router)
app.include_router(student_support_router)
