from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.deps import require_admin_or_bootstrap
from app.core.security import hash_password
from app.db import models
from app.db.postgres import get_session
from app.repositories.graph_repository import GraphRepository
from app.repositories.postgres_repository import PostgresRepository
from app.schemas.internal import (
    DeriveEvidenceResponse,
    GenerateSyntheticDataRequest,
    GenerateSyntheticDataResponse,
    ImportCurriculumResponse,
    ImportRiskModelResponse,
    ProjectGraphResponse,
    SeedSchoolDataRequest,
    SeedSchoolDataResponse,
)
from app.services.curriculum_service import load_json, validate_curriculum
from app.services.dropout_risk import get_explainer, load_risk_copy
from app.services.graph_projection import (
    build_evidence_payload,
    build_mastery_payload,
    build_peer_payload,
    build_risk_payload,
    enrich_edges_with_narrative,
    risk_factor_payload,
)
from app.services.school_seed import (
    derive_academic_performance_evidence,
    generate_school_seed,
)
from app.services.synthetic_data import StudentAcademicProfile, generate_synthetic_dataset

router = APIRouter(
    prefix="/internal",
    tags=["internal"],
    # Administrators only, except while the database has no accounts at all --
    # the seed creates the first administrator, so requiring one would deadlock.
    dependencies=[Depends(require_admin_or_bootstrap)],
)


@router.post("/import/curriculum", response_model=ImportCurriculumResponse)
def import_curriculum() -> ImportCurriculumResponse:
    curriculum = load_json(settings.curriculum_path)
    validate_curriculum(curriculum)
    repository = GraphRepository()
    try:
        summary = repository.import_curriculum(
            curriculum["subjects"],
            curriculum["concepts"],
            [tuple(edge) for edge in curriculum["edges"]],
        )
    finally:
        repository.close()
    return ImportCurriculumResponse(**summary, source=str(settings.curriculum_path))


@router.post("/import/risk-model", response_model=ImportRiskModelResponse)
def import_risk_model(request: Request) -> ImportRiskModelResponse:
    """Load the causal DAG into Neo4j so risk explanations become graph traversals."""
    copy = load_risk_copy(str(settings.risk_factor_copy_path))
    factors, edges = risk_factor_payload(copy)

    ui_data_path = (
        settings.risk_factor_copy_path.parents[2]
        / "research"
        / "dropout-ews"
        / "ui"
        / "ui_data.json"
    )
    ui_data = None
    if ui_data_path.exists():
        ui_data = load_json(ui_data_path)
    edges = enrich_edges_with_narrative(edges, ui_data)

    repository = GraphRepository()
    try:
        summary = repository.import_risk_model(factors, edges)
    finally:
        repository.close()
    risk_model = request.app.state.risk_model
    return ImportRiskModelResponse(
        model_variant=risk_model.variant.value,
        model_fingerprint=risk_model.fingerprint,
        **summary,
    )


@router.post("/project/graph", response_model=ProjectGraphResponse)
def project_graph(
    request: Request, session: Session = Depends(get_session)
) -> ProjectGraphResponse:
    """Project schools, classes, teachers, students, mastery, evidence and peers.

    Run after seeding and after generating academic evidence: the graph is a derived
    view, so it is rebuilt rather than incrementally maintained.
    """
    copy = load_risk_copy(str(settings.risk_factor_copy_path))
    explainer = get_explainer(request.app)
    repository = PostgresRepository(session)

    term = repository.get_current_term()
    if term is None:
        raise HTTPException(status_code=404, detail="Seed the school data first.")

    students = repository.list_students(limit=5000)
    student_ids = [student["id"] for student in students]
    evidence_by_student = repository.get_risk_evidence_bulk(student_ids, term.id)
    sources_by_student = {
        student_id: {
            variable: row["source"]
            for variable, row in repository.get_risk_evidence(student_id, term.id).items()
        }
        for student_id in student_ids
    }

    graph = GraphRepository()
    try:
        summary = graph.project_school_graph(
            schools=repository.list_schools(),
            classes=repository.list_classes(),
            teachers=[
                {
                    "id": teacher.id,
                    "school_id": teacher.school_id,
                    "full_name": teacher.full_name,
                    "full_name_si": teacher.full_name_si,
                    "role_title": teacher.role_title,
                }
                for teacher in session.query(models.Teacher).all()
            ],
            students=students,
            mastery=build_mastery_payload(repository.latest_scores_by_student()),
            evidence=build_evidence_payload(evidence_by_student, sources_by_student, copy),
            peers=build_peer_payload(students, evidence_by_student),
            risk=build_risk_payload(evidence_by_student, explainer),
        )
    finally:
        graph.close()
    return ProjectGraphResponse(**summary)


@router.post("/seed/school-data", response_model=SeedSchoolDataResponse)
def seed_school_data(
    payload: SeedSchoolDataRequest,
    request: Request,
    session: Session = Depends(get_session),
) -> SeedSchoolDataResponse:
    """Seed schools, classes, teachers, students, login accounts and wellbeing evidence.

    Destructive: replaces the entire roster and every record keyed on it.
    """
    seed = generate_school_seed(
        roster_path=settings.school_roster_path,
        risk_model=request.app.state.risk_model,
        password_hasher=hash_password,
        students_per_class=payload.students_per_class or 20,
        seed_override=payload.seed,
    )
    repository = PostgresRepository(session)
    summary = repository.replace_school_data(seed)
    return SeedSchoolDataResponse(
        seed=seed.seed,
        demo_credentials=seed.credentials,
        **summary,
    )


@router.post("/generate/synthetic-data", response_model=GenerateSyntheticDataResponse)
def generate_synthetic_data(
    payload: GenerateSyntheticDataRequest,
    session: Session = Depends(get_session),
) -> GenerateSyntheticDataResponse:
    """Generate assessment evidence for the learners already in the roster.

    Each learner's mastery is depressed by an academic penalty derived from their own
    wellbeing evidence, so the academic and risk pictures describe the same child.
    """
    curriculum = load_json(settings.curriculum_path)
    repository = PostgresRepository(session)
    students = repository.list_students(limit=5000)
    term = repository.get_current_term()

    penalties: dict[str, float] = {}
    if term is not None:
        evidence = repository.get_risk_evidence_bulk([s["id"] for s in students], term.id)
        from app.services.school_seed import _academic_penalty

        penalties = {
            student_id: _academic_penalty(variables)
            for student_id, variables in evidence.items()
        }

    profiles = [
        StudentAcademicProfile(
            student_id=student["id"],
            academic_penalty=penalties.get(student["id"], 0.0),
        )
        for student in students
    ]

    dataset = generate_synthetic_dataset(
        curriculum=curriculum,
        config_path=settings.generator_config_path,
        profiles=profiles,
        seed_override=payload.seed,
    )
    summary = repository.replace_academic_data(
        assessments=dataset.assessments,
        questions=dataset.questions,
        question_results=dataset.question_results,
        concept_scores=dataset.concept_scores,
    )
    return GenerateSyntheticDataResponse(seed=dataset.seed, **summary)


@router.post("/generate/evidence", response_model=DeriveEvidenceResponse)
def derive_evidence(session: Session = Depends(get_session)) -> DeriveEvidenceResponse:
    """Derive `Current_Academic_Performance` from real concept scores.

    This is the join between the two halves of the system: the one signal node a school
    genuinely observes is computed from the learner's own assessment evidence rather
    than sampled.
    """
    repository = PostgresRepository(session)
    term = repository.get_current_term()
    if term is None:
        return DeriveEvidenceResponse(
            term_id="", derived_count=0, variable="Current_Academic_Performance"
        )

    averages = repository.average_mastery_by_student()
    derived = 0
    for student_id, average in averages.items():
        row = derive_academic_performance_evidence(
            student_id=student_id, term_id=term.id, average_mastery=average
        )
        if row is None:
            continue
        repository.upsert_risk_evidence(
            student_id=student_id,
            term_id=term.id,
            variable=row.variable,
            state=row.state,
            source="derived",
            recorded_by=None,
            note=row.note,
        )
        derived += 1
    session.commit()
    return DeriveEvidenceResponse(
        term_id=term.id, derived_count=derived, variable="Current_Academic_Performance"
    )
