from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.postgres import get_session
from app.repositories.graph_repository import GraphRepository
from app.repositories.postgres_repository import PostgresRepository
from app.schemas.learning import (
    LearningProfileResponse,
    QuizAttemptResponse,
    QuizStartRequest,
    QuizSubmitRequest,
    QuizSubmitResponse,
)
from app.services.learning import (
    build_learning_profile,
    ensure_quiz_questions_seeded,
    question_counts_by_concept,
    start_quiz_attempt,
    submit_quiz_attempt,
)
from app.services.subject_diagnosis import SubjectDiagnosisEngine


router = APIRouter(prefix="/api/learn", tags=["learning"])


def _load_subject_map(student_id: str, subject_id: str, session: Session):
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


@router.get("/student/{student_id}/subject/{subject_id}", response_model=LearningProfileResponse)
def get_learning_profile(
    student_id: str,
    subject_id: str,
    session: Session = Depends(get_session),
) -> LearningProfileResponse:
    ensure_quiz_questions_seeded(session, settings.quiz_bank_path)
    subject_map = _load_subject_map(student_id, subject_id, session)
    return build_learning_profile(
        subject_map=subject_map,
        question_count_by_concept=question_counts_by_concept(session, subject_id),
    )


@router.post("/quiz/start", response_model=QuizAttemptResponse)
def start_quiz(
    payload: QuizStartRequest,
    session: Session = Depends(get_session),
) -> QuizAttemptResponse:
    ensure_quiz_questions_seeded(session, settings.quiz_bank_path)
    subject_map = _load_subject_map(payload.student_id, payload.subject_id, session)
    requested_concepts = payload.concept_ids or [
        node.id
        for node in sorted(
            subject_map.concepts,
            key=lambda node: (
                {"support_now": 0, "watch": 1, "missing_evidence": 2, "ready": 3}.get(node.status, 9),
                -node.priority_score,
                node.depth,
                node.id,
            ),
        )[:3]
    ]
    valid_concepts = {concept.id for concept in subject_map.concepts}
    selected_concepts = [concept_id for concept_id in requested_concepts if concept_id in valid_concepts][:3]
    if not selected_concepts:
        raise HTTPException(status_code=400, detail="No valid concepts available for this quiz.")

    attempt = start_quiz_attempt(
        session=session,
        student_id=payload.student_id,
        subject_id=payload.subject_id,
        concept_ids=selected_concepts,
        quiz_length=payload.quiz_length,
        concept_names={concept.id: concept.name for concept in subject_map.concepts},
        quiz_bank_path=settings.quiz_bank_path,
    )
    if not attempt.questions:
        raise HTTPException(status_code=404, detail="No quiz questions available for the selected concepts.")
    return attempt


@router.post("/quiz/{attempt_id}/submit", response_model=QuizSubmitResponse)
def submit_quiz(
    attempt_id: str,
    payload: QuizSubmitRequest,
    session: Session = Depends(get_session),
) -> QuizSubmitResponse:
    try:
        return submit_quiz_attempt(
            session=session,
            attempt_id=attempt_id,
            answers={answer.question_id: answer.selected_option_index for answer in payload.answers},
            quiz_bank_path=settings.quiz_bank_path,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
