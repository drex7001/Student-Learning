from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import CurrentUser, deny_students, require_staff
from app.db.postgres import get_session
from app.repositories.graph_repository import GraphRepository
from app.repositories.postgres_repository import PostgresRepository
from app.risk import dropout_ews_bn as bn
from app.services.dropout_risk import load_risk_copy

router = APIRouter(prefix="/api/graph", tags=["graph"])


def _copy():
    return load_risk_copy(str(settings.risk_factor_copy_path))


@router.get("/students/{student_id}/neighbourhood")
def student_neighbourhood(
    student_id: str, user: CurrentUser = Depends(require_staff)
) -> dict:
    """Everything connected to one learner, in a single traversal.

    Class, school, class teachers, weak concepts, concern factors and peers -- the
    relational schema needs five joins for this; the graph needs one query.
    """
    deny_students(user)
    repository = GraphRepository()
    try:
        neighbourhood = repository.get_student_neighbourhood(student_id)
        if not neighbourhood or neighbourhood.get("student") is None:
            raise HTTPException(status_code=404, detail="Student not in the graph projection.")
        neighbourhood["root_causes"] = repository.get_concept_root_causes(student_id)
    finally:
        repository.close()
    return neighbourhood


@router.get("/students/{student_id}/causal-paths/{variable}")
def causal_paths(
    student_id: str,
    variable: str,
    user: CurrentUser = Depends(require_staff),
) -> dict:
    """How a factor reaches the outcome, read off the causal graph.

    This is the "Why this flag?" surface. Every route runs through a mechanism a
    school can act on -- there is no direct edge from a protected characteristic to
    the outcome, and the graph is where that is visible rather than merely asserted.
    """
    deny_students(user)
    copy = _copy()
    if variable not in bn.NODE_STATES:
        raise HTTPException(status_code=404, detail="Unknown risk factor.")
    repository = GraphRepository()
    try:
        paths = repository.get_causal_paths(variable, copy.target)
    finally:
        repository.close()
    return {
        "variable": variable,
        "label": copy.label(variable),
        "target": copy.target,
        "path_count": len(paths),
        "paths": paths,
        "note": (
            "Every route passes through something a school can change. A protected "
            "characteristic never reaches the outcome directly."
        ),
    }


@router.get("/shared-factors")
def shared_factors(
    school_id: str | None = Query(default=None),
    class_id: str | None = Query(default=None),
    user: CurrentUser = Depends(require_staff),
    session: Session = Depends(get_session),
) -> dict:
    """Concerns many learners share.

    Reads as a maintenance list for the school, not a watchlist of children. A factor
    that a third of a school carries is a condition of the building or the staffing,
    and fixing it helps everyone in it.
    """
    deny_students(user)
    repository = GraphRepository()
    try:
        rows = repository.get_shared_factors(school_id=school_id, class_id=class_id)
    finally:
        repository.close()

    postgres = PostgresRepository(session)
    population = len(
        postgres.list_students(limit=2000, school_id=school_id, class_id=class_id)
    )
    for row in rows:
        row["share"] = round(row["affected"] / population, 4) if population else 0.0
        row["school_level"] = bool(row["modifiable"]) and row["share"] >= 0.30
    return {
        "school_id": school_id,
        "class_id": class_id,
        "population": population,
        "factors": rows,
        "note": (
            "A concern shared this widely is a condition of the school, not a property "
            "of the students who carry it."
        ),
    }


@router.get("/classes/{class_id}/peers")
def peer_network(
    class_id: str, user: CurrentUser = Depends(require_staff)
) -> dict:
    """Peer ties inside a class, with tie counts for the isolation view."""
    deny_students(user)
    repository = GraphRepository()
    try:
        network = repository.get_peer_network(class_id)
    finally:
        repository.close()
    if not network["nodes"]:
        raise HTTPException(status_code=404, detail="Class not in the graph projection.")

    ties = [node["ties"] for node in network["nodes"]]
    average = round(sum(ties) / len(ties), 2) if ties else 0.0
    network["summary"] = {
        "class_id": class_id,
        "students": len(network["nodes"]),
        "average_ties": average,
        "few_ties": sum(1 for count in ties if count <= 1),
    }
    network["note"] = (
        "Peer ties in this prototype are generated, not surveyed, and are shaped by the "
        "recorded evidence. Few ties is a prompt to look, never a finding about a child."
    )
    return network
