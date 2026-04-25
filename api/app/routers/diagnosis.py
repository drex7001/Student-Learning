from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.postgres import get_session
from app.repositories.graph_repository import GraphRepository
from app.repositories.postgres_repository import PostgresRepository
from app.schemas.diagnosis import (
    ConceptNode,
    DiagnosisResponse,
    PrerequisiteResponse,
    SelectorOptionsResponse,
    SubjectNode,
    SubjectDiagnosisMapResponse,
    SupportQueueEntry,
    SupportQueueResponse,
    SupportQueueSummary,
)
from app.services.diagnosis import DiagnosisEngine
from app.services.subject_diagnosis import SubjectDiagnosisEngine


router = APIRouter(prefix="/api", tags=["diagnosis"])


@router.get("/options", response_model=SelectorOptionsResponse)
def get_selector_options(
    subject_id: str | None = None,
    session: Session = Depends(get_session),
) -> SelectorOptionsResponse:
    graph_repository = GraphRepository()
    try:
        subjects = graph_repository.list_subjects()
        concepts = graph_repository.list_concepts(subject_id)
    finally:
        graph_repository.close()

    students = PostgresRepository(session).list_students()
    return SelectorOptionsResponse(
        students=students,
        subjects=subjects,
        concepts=concepts,
    )


@router.get("/subjects", response_model=list[SubjectNode])
def get_subjects() -> list[SubjectNode]:
    graph_repository = GraphRepository()
    try:
        subjects = graph_repository.list_subjects()
    finally:
        graph_repository.close()
    return [SubjectNode(**subject) for subject in subjects]


@router.get("/concepts/{concept_id}/prerequisites", response_model=PrerequisiteResponse)
def get_prerequisites(concept_id: str) -> PrerequisiteResponse:
    graph_repository = GraphRepository()
    try:
        concept = graph_repository.get_concept(concept_id)
        if concept is None:
            raise HTTPException(status_code=404, detail="Concept not found.")
        prerequisite_paths = graph_repository.get_prerequisite_paths(concept_id)
        downstream = graph_repository.get_downstream_concepts(concept_id)
    finally:
        graph_repository.close()

    return PrerequisiteResponse(
        concept=ConceptNode(**concept),
        prerequisite_paths=[
            {"path_index": index, "nodes": path}
            for index, path in enumerate(prerequisite_paths, start=1)
        ],
        downstream_concepts=[ConceptNode(**node) for node in downstream],
    )


@router.get("/diagnosis/student/{student_id}/concept/{concept_id}", response_model=DiagnosisResponse)
def get_diagnosis(student_id: str, concept_id: str, session: Session = Depends(get_session)) -> DiagnosisResponse:
    postgres_repository = PostgresRepository(session)
    student = postgres_repository.get_student(student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Student data not found. Generate synthetic data first.")

    graph_repository = GraphRepository()
    try:
        concept = graph_repository.get_concept(concept_id)
        if concept is None:
            raise HTTPException(status_code=404, detail="Concept not found.")
        prerequisite_paths = graph_repository.get_prerequisite_paths(concept_id)
    finally:
        graph_repository.close()

    if not prerequisite_paths:
        raise HTTPException(status_code=404, detail="Prerequisite paths not found. Import the curriculum first.")

    latest_scores = postgres_repository.get_latest_scores_for_student(student_id)
    if not latest_scores:
        raise HTTPException(status_code=404, detail="Student data not found. Generate synthetic data first.")

    concept_ids_for_trends = list(
        {
            node["id"]
            for path in prerequisite_paths
            for node in path
        }
    )
    recent_scores_by_concept = postgres_repository.get_recent_scores_for_student(
        student_id,
        concept_ids_for_trends,
    )
    assessment_summary = postgres_repository.get_student_assessment_summary(student_id)
    cohort_target_mastery = postgres_repository.get_latest_cohort_mastery(student["cohort"], concept_id)

    return DiagnosisEngine().run(
        student_id=student_id,
        student=student,
        target_concept=concept,
        prerequisite_paths=prerequisite_paths,
        latest_scores=latest_scores,
        recent_scores_by_concept=recent_scores_by_concept,
        assessment_summary=assessment_summary,
        cohort_target_mastery=cohort_target_mastery,
    )


@router.get("/diagnosis/student/{student_id}/subject/{subject_id}/map", response_model=SubjectDiagnosisMapResponse)
def get_subject_diagnosis_map(
    student_id: str,
    subject_id: str,
    session: Session = Depends(get_session),
) -> SubjectDiagnosisMapResponse:
    postgres_repository = PostgresRepository(session)
    student = postgres_repository.get_student(student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Student data not found. Generate synthetic data first.")

    graph_repository = GraphRepository()
    try:
        subject = graph_repository.get_subject(subject_id)
        if subject is None:
            raise HTTPException(status_code=404, detail="Subject not found.")
        concepts = graph_repository.list_concepts(subject_id)
        edges = graph_repository.get_subject_edges(subject_id)
    finally:
        graph_repository.close()

    if not concepts:
        raise HTTPException(status_code=404, detail="Subject concepts not found. Import the curriculum first.")

    latest_scores = postgres_repository.get_latest_scores_for_student(student_id)
    if not latest_scores:
        raise HTTPException(status_code=404, detail="Student data not found. Generate synthetic data first.")

    return SubjectDiagnosisEngine().run(
        student=student,
        subject=subject,
        concepts=concepts,
        edges=edges,
        latest_scores=latest_scores,
    )


@router.get("/overview/concept/{concept_id}", response_model=SupportQueueResponse)
def get_support_queue(
    concept_id: str,
    limit: int = 18,
    session: Session = Depends(get_session),
) -> SupportQueueResponse:
    graph_repository = GraphRepository()
    try:
        concept = graph_repository.get_concept(concept_id)
        if concept is None:
            raise HTTPException(status_code=404, detail="Concept not found.")
        prerequisite_paths = graph_repository.get_prerequisite_paths(concept_id)
    finally:
        graph_repository.close()

    if not prerequisite_paths:
        raise HTTPException(status_code=404, detail="Prerequisite paths not found. Import the curriculum first.")

    postgres_repository = PostgresRepository(session)
    students = postgres_repository.list_students()
    diagnosis_engine = DiagnosisEngine()
    cohort_mastery_cache: dict[str, float | None] = {}
    entries: list[SupportQueueEntry] = []

    for student in students:
        latest_scores = postgres_repository.get_latest_scores_for_student(student["id"])
        if not latest_scores:
            continue

        cohort = student["cohort"]
        if cohort not in cohort_mastery_cache:
            cohort_mastery_cache[cohort] = postgres_repository.get_latest_cohort_mastery(cohort, concept_id)

        diagnosis = diagnosis_engine.run(
            student_id=student["id"],
            student=student,
            target_concept=concept,
            prerequisite_paths=prerequisite_paths,
            latest_scores=latest_scores,
            recent_scores_by_concept={},
            assessment_summary=postgres_repository.get_student_assessment_summary(student["id"]),
            cohort_target_mastery=cohort_mastery_cache[cohort],
        )
        entries.append(
            SupportQueueEntry(
                student_id=student["id"],
                student_name=student["full_name"],
                cohort=student["cohort"],
                readiness_status=diagnosis.readiness.status,
                readiness_score=diagnosis.readiness.readiness_score,
                target_mastery=diagnosis.readiness.target_mastery,
                cohort_gap=diagnosis.readiness.cohort_gap,
                latest_assessment_date=diagnosis.readiness.latest_assessment_date,
                top_root_cause=(
                    diagnosis.root_cause_candidates[0].concept_name
                    if diagnosis.root_cause_candidates
                    else None
                ),
            )
        )

    entries.sort(key=lambda item: (item.readiness_score, item.target_mastery, item.student_id))
    selected_entries = entries[: max(1, min(limit, 40))]
    summary = SupportQueueSummary(
        total_students=len(entries),
        support_now=sum(1 for item in entries if item.readiness_status == "needs_immediate_support"),
        watch_list=sum(1 for item in entries if item.readiness_status == "watch"),
        ready_to_progress=sum(1 for item in entries if item.readiness_status == "ready_to_progress"),
    )

    return SupportQueueResponse(
        concept=ConceptNode(**concept),
        summary=summary,
        students=selected_entries,
    )
