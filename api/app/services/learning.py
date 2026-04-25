from __future__ import annotations

import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import Path
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.db import models
from app.schemas.diagnosis import SubjectDiagnosisMapResponse
from app.schemas.learning import (
    LearningProfileResponse,
    LessonCard,
    QuizAnswerResult,
    QuizAttemptResponse,
    QuizQuestionItem,
    QuizSubmitResponse,
    RecommendedQuiz,
    UpdatedConceptScore,
)
from app.services.scoring import calculate_confidence


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _decode_json_list(value: str) -> list:
    return json.loads(value)


def _encode_json(value: object) -> str:
    return json.dumps(value, ensure_ascii=False)


def ensure_quiz_questions_seeded(session: Session, quiz_bank_path: Path) -> None:
    bank = _load_json(quiz_bank_path)
    for item in bank["questions"]:
        if session.get(models.QuizQuestion, item["id"]) is not None:
            continue
        session.add(
            models.QuizQuestion(
                id=item["id"],
                subject_id=item["subject_id"],
                concept_id=item["concept_id"],
                prompt=item["prompt"],
                options_json=_encode_json(item["options"]),
                correct_option_index=item["correct_option_index"],
                explanation=item["explanation"],
                difficulty=item["difficulty"],
            )
        )
    try:
        session.commit()
    except IntegrityError:
        session.rollback()


def build_learning_profile(
    *,
    subject_map: SubjectDiagnosisMapResponse,
    question_count_by_concept: dict[str, int],
) -> LearningProfileResponse:
    recommended_nodes = _recommended_nodes(subject_map)
    lesson_cards = [
        LessonCard(
            concept_id=node.id,
            concept_name=node.name,
            concept_name_si=node.name_si,
            status=node.status,
            mastery_score=node.mastery_score,
            confidence=node.confidence,
            priority_score=node.priority_score,
            why_it_matters=node.description
            or f"{node.name} supports later work in {subject_map.subject.name}.",
            study_tips=_study_tips(node.status, node.name),
        )
        for node in recommended_nodes[:6]
    ]
    quiz_concept_ids = [node.id for node in recommended_nodes[:3]]
    question_count = sum(question_count_by_concept.get(concept_id, 0) for concept_id in quiz_concept_ids)

    return LearningProfileResponse(
        student=subject_map.student,
        subject=subject_map.subject,
        summary=subject_map.summary,
        recommended_concepts=recommended_nodes[:6],
        lesson_cards=lesson_cards,
        recommended_quiz=RecommendedQuiz(
            concept_ids=quiz_concept_ids,
            question_count=question_count,
            reason="Selected from the highest-priority support and watch concepts.",
        ),
    )


def start_quiz_attempt(
    *,
    session: Session,
    student_id: str,
    subject_id: str,
    concept_ids: list[str],
    quiz_length: int,
    concept_names: dict[str, str],
) -> QuizAttemptResponse:
    selected_questions = _select_questions(session, subject_id, concept_ids, quiz_length)
    selected_concept_ids = sorted({question.concept_id for question in selected_questions})
    attempt = models.QuizAttempt(
        id=f"QA-{uuid4().hex[:12].upper()}",
        student_id=student_id,
        subject_id=subject_id,
        concept_ids_json=_encode_json(selected_concept_ids),
        question_ids_json=_encode_json([question.id for question in selected_questions]),
        status="in_progress",
        started_at=datetime.now(),
        submitted_at=None,
    )
    session.add(attempt)
    session.commit()

    return QuizAttemptResponse(
        attempt_id=attempt.id,
        student_id=student_id,
        subject_id=subject_id,
        concept_ids=selected_concept_ids,
        status=attempt.status,
        questions=[
            QuizQuestionItem(
                id=question.id,
                concept_id=question.concept_id,
                concept_name=concept_names.get(question.concept_id, question.concept_id),
                prompt=question.prompt,
                options=_decode_json_list(question.options_json),
                difficulty=question.difficulty,
            )
            for question in selected_questions
        ],
    )


def submit_quiz_attempt(
    *,
    session: Session,
    attempt_id: str,
    answers: dict[str, int | None],
) -> QuizSubmitResponse:
    attempt = session.get(models.QuizAttempt, attempt_id)
    if attempt is None:
        raise ValueError("Quiz attempt not found.")
    if attempt.status != "in_progress":
        raise ValueError("Quiz attempt has already been submitted.")

    question_ids = _decode_json_list(attempt.question_ids_json)
    questions = session.execute(
        select(models.QuizQuestion).where(models.QuizQuestion.id.in_(question_ids)).order_by(models.QuizQuestion.id)
    ).scalars().all()
    question_by_id = {question.id: question for question in questions}
    ordered_questions = [question_by_id[question_id] for question_id in question_ids if question_id in question_by_id]

    submitted_at = datetime.now()
    attempt.status = "submitted"
    attempt.submitted_at = submitted_at

    concept_scores: dict[str, list[float]] = defaultdict(list)
    concept_answered_counts: dict[str, int] = defaultdict(int)
    concept_mapped_counts: dict[str, int] = defaultdict(int)
    results: list[QuizAnswerResult] = []

    for question in ordered_questions:
        selected = answers.get(question.id)
        is_answered = selected is not None
        is_correct = is_answered and selected == question.correct_option_index
        score = 1.0 if is_correct else 0.0
        concept_scores[question.concept_id].append(score)
        concept_mapped_counts[question.concept_id] += 1
        if is_answered:
            concept_answered_counts[question.concept_id] += 1

        session.add(
            models.QuizAnswer(
                id=f"QANS-{attempt.id}-{question.id}",
                attempt_id=attempt.id,
                question_id=question.id,
                concept_id=question.concept_id,
                selected_option_index=selected,
                is_correct=1 if is_correct else 0,
                score_obtained=score,
                score_max=1.0,
            )
        )
        results.append(
            QuizAnswerResult(
                question_id=question.id,
                concept_id=question.concept_id,
                prompt=question.prompt,
                selected_option_index=selected,
                correct_option_index=question.correct_option_index,
                is_correct=bool(is_correct),
                score_obtained=score,
                score_max=1.0,
                explanation=question.explanation,
            )
        )

    assessment_id = f"PRACTICE-{attempt.id}"
    attempt_number = _next_attempt_number(session, attempt.student_id)
    session.add(
        models.Assessment(
            id=assessment_id,
            student_id=attempt.student_id,
            assessment_date=date.today(),
            attempt_number=attempt_number,
        )
    )

    for question in ordered_questions:
        practice_question_id = f"PRACTICE-{question.id}"
        if session.get(models.Question, practice_question_id) is None:
            session.add(
                models.Question(
                    id=practice_question_id,
                    concept_id=question.concept_id,
                    prompt=question.prompt,
                    score_max=1.0,
                )
            )
        answer_result = next(result for result in results if result.question_id == question.id)
        session.add(
            models.QuestionResult(
                id=f"PRES-{attempt.id}-{question.id}",
                assessment_id=assessment_id,
                question_id=practice_question_id,
                concept_id=question.concept_id,
                score_obtained=answer_result.score_obtained,
                score_max=1.0,
            )
        )

    updated_concepts: list[UpdatedConceptScore] = []
    for concept_id, scores in concept_scores.items():
        mapped_count = concept_mapped_counts[concept_id]
        answered_count = concept_answered_counts[concept_id]
        mastery = round(sum(scores) / max(1, mapped_count), 4)
        confidence = calculate_confidence(answered_count, mapped_count)
        session.add(
            models.ConceptScore(
                id=f"PCS-{attempt.id}-{concept_id}",
                student_id=attempt.student_id,
                assessment_id=assessment_id,
                concept_id=concept_id,
                mastery_score=mastery,
                confidence=confidence,
                computed_at=submitted_at,
            )
        )
        updated_concepts.append(
            UpdatedConceptScore(
                concept_id=concept_id,
                mastery_score=mastery,
                confidence=confidence,
                answered_question_count=answered_count,
                mapped_question_count=mapped_count,
            )
        )

    session.commit()
    total_score = round(sum(result.score_obtained for result in results), 4)
    total_max = round(sum(result.score_max for result in results), 4)
    return QuizSubmitResponse(
        attempt_id=attempt.id,
        status=attempt.status,
        score_obtained=total_score,
        score_max=total_max,
        percentage=round(total_score / total_max, 4) if total_max else 0,
        results=results,
        updated_concepts=sorted(updated_concepts, key=lambda item: item.concept_id),
    )


def question_counts_by_concept(session: Session, subject_id: str) -> dict[str, int]:
    rows = session.execute(
        select(models.QuizQuestion.concept_id, func.count(models.QuizQuestion.id))
        .where(models.QuizQuestion.subject_id == subject_id)
        .group_by(models.QuizQuestion.concept_id)
    ).all()
    return {concept_id: count for concept_id, count in rows}


def _recommended_nodes(subject_map: SubjectDiagnosisMapResponse):
    order = {"support_now": 0, "watch": 1, "missing_evidence": 2, "ready": 3}
    return sorted(
        subject_map.concepts,
        key=lambda node: (order.get(node.status, 9), -node.priority_score, node.depth, node.id),
    )


def _study_tips(status: str, concept_name: str) -> list[str]:
    if status == "support_now":
        return [
            f"Review the basic meaning of {concept_name.lower()} before solving exam-style questions.",
            "Work slowly through one example and name each step.",
            "Retry missed quiz questions and read the explanation before moving on.",
        ]
    if status == "watch":
        return [
            "Check the common mistake for this concept before practice.",
            "Do a short quiz and focus on accuracy, not speed.",
            "Explain your answer in one sentence after each question.",
        ]
    if status == "missing_evidence":
        return [
            "Take a short quiz so the system has recent evidence.",
            "Start with the easiest example and check the feedback.",
            "Use the explanation after each answer to fill gaps.",
        ]
    return [
        "Use this concept in mixed problems to keep it strong.",
        "Try one harder question after revision.",
        "Connect this concept to the next topic in the subject path.",
    ]


def _select_questions(
    session: Session,
    subject_id: str,
    concept_ids: list[str],
    quiz_length: int,
) -> list[models.QuizQuestion]:
    selected_concepts = concept_ids[:3]
    if not selected_concepts:
        return []
    questions = session.execute(
        select(models.QuizQuestion)
        .where(
            models.QuizQuestion.subject_id == subject_id,
            models.QuizQuestion.concept_id.in_(selected_concepts),
        )
        .order_by(models.QuizQuestion.difficulty, models.QuizQuestion.id)
    ).scalars().all()
    return questions[:quiz_length]


def _next_attempt_number(session: Session, student_id: str) -> int:
    max_attempt = session.scalar(
        select(func.max(models.Assessment.attempt_number)).where(models.Assessment.student_id == student_id)
    )
    return int(max_attempt or 0) + 1
