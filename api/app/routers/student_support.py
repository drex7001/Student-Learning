from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.db.postgres import get_session
from app.repositories.graph_repository import GraphRepository
from app.repositories.postgres_repository import PostgresRepository
from app.schemas.diagnosis import SubjectNode
from app.schemas.student_support import (
    StudentSupportEntry,
    StudentSupportListResponse,
    StudentSupportProfileResponse,
    StudentSupportSummary,
)
from app.services.student_support import StudentSupportEngine

router = APIRouter(prefix="/api", tags=["student-support"])


def _load_subject_context(subject_id: str) -> tuple[dict, list[dict], list[dict]]:
    graph_repository = GraphRepository()
    try:
        subject = graph_repository.get_subject(subject_id)
        if subject is None:
            raise HTTPException(status_code=404, detail="Subject not found. Import the curriculum first.")
        concepts = graph_repository.list_concepts(subject_id)
        if not concepts:
            raise HTTPException(status_code=404, detail="Subject concepts not found. Import the curriculum first.")
        edges = graph_repository.get_subject_edges(subject_id)
    finally:
        graph_repository.close()
    return subject, concepts, edges


def _build_profile_for_student(
    *,
    student: dict,
    subject: dict,
    concepts: list[dict],
    edges: list[dict],
    postgres_repository: PostgresRepository,
    cohort_mastery_cache: dict[tuple[str, str], float | None],
    engine: StudentSupportEngine,
) -> StudentSupportProfileResponse:
    concept_ids = [concept["id"] for concept in concepts]
    latest_scores = postgres_repository.get_latest_scores_for_student(student["id"])
    recent_scores_by_concept = postgres_repository.get_recent_scores_for_student(
        student["id"],
        concept_ids,
        limit_per_concept=2,
    )
    cohort_mastery_by_concept: dict[str, float | None] = {}
    for concept_id in concept_ids:
        cache_key = (student["cohort"], concept_id)
        if cache_key not in cohort_mastery_cache:
            cohort_mastery_cache[cache_key] = postgres_repository.get_latest_cohort_mastery(
                student["cohort"],
                concept_id,
            )
        cohort_mastery_by_concept[concept_id] = cohort_mastery_cache[cache_key]

    return engine.build_profile(
        student=student,
        subject=subject,
        concepts=concepts,
        edges=edges,
        latest_scores=latest_scores,
        recent_scores_by_concept=recent_scores_by_concept,
        cohort_mastery_by_concept=cohort_mastery_by_concept,
        assessment_summary=postgres_repository.get_student_assessment_summary(student["id"]),
    )


@router.get("/support/subjects/{subject_id}/students", response_model=StudentSupportListResponse)
def list_student_support_risks(
    subject_id: str,
    limit: int = Query(default=40, ge=1, le=120),
    session: Session = Depends(get_session),
) -> StudentSupportListResponse:
    subject, concepts, edges = _load_subject_context(subject_id)
    postgres_repository = PostgresRepository(session)
    students = postgres_repository.list_students(limit=250)
    engine = StudentSupportEngine()
    cohort_mastery_cache: dict[tuple[str, str], float | None] = {}
    profiles: list[StudentSupportProfileResponse] = []

    for student in students:
        profiles.append(
            _build_profile_for_student(
                student=student,
                subject=subject,
                concepts=concepts,
                edges=edges,
                postgres_repository=postgres_repository,
                cohort_mastery_cache=cohort_mastery_cache,
                engine=engine,
            )
        )

    profiles.sort(key=lambda profile: (-profile.risk.score, profile.student.id))
    selected_profiles = profiles[:limit]
    entries = [
        StudentSupportEntry(
            student_id=profile.student.id,
            student_name=profile.student.full_name,
            cohort=profile.student.cohort,
            risk_score=profile.risk.score,
            risk_band=profile.risk.band,
            confidence=profile.risk.confidence,
            top_reason=(profile.factors[0].label if profile.factors else None),
            recommended_action=profile.recommended_actions[0],
        )
        for profile in selected_profiles
    ]

    total_profiles = len(profiles)
    average_confidence = (
        round(sum(profile.risk.confidence for profile in profiles) / total_profiles, 4)
        if total_profiles
        else 0.0
    )
    summary = StudentSupportSummary(
        total_students=total_profiles,
        high_support=sum(1 for profile in profiles if profile.risk.band == "high_support"),
        watch=sum(1 for profile in profiles if profile.risk.band == "watch"),
        stable=sum(1 for profile in profiles if profile.risk.band == "stable"),
        average_confidence=average_confidence,
    )
    return StudentSupportListResponse(
        subject=SubjectNode(**subject),
        summary=summary,
        students=entries,
    )


@router.get("/support/students/{student_id}/subjects/{subject_id}", response_model=StudentSupportProfileResponse)
def get_student_support_profile(
    student_id: str,
    subject_id: str,
    session: Session = Depends(get_session),
) -> StudentSupportProfileResponse:
    subject, concepts, edges = _load_subject_context(subject_id)
    postgres_repository = PostgresRepository(session)
    student = postgres_repository.get_student(student_id)
    if student is None:
        raise HTTPException(status_code=404, detail="Student data not found. Generate synthetic data first.")

    return _build_profile_for_student(
        student=student,
        subject=subject,
        concepts=concepts,
        edges=edges,
        postgres_repository=postgres_repository,
        cohort_mastery_cache={},
        engine=StudentSupportEngine(),
    )
