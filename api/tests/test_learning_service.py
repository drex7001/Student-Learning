from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import sessionmaker

from app.db import models
from app.db.postgres import Base
from app.schemas.diagnosis import ConceptSupportNode, StudentSummary, SubjectDiagnosisMapResponse, SubjectNode, SubjectSupportSummary
from app.services.learning import build_learning_profile, ensure_quiz_questions_seeded, start_quiz_attempt, submit_quiz_attempt


def make_session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    session_factory = sessionmaker(bind=engine)
    return session_factory()


def seed_quiz_data(session):
    session.add(models.Student(id="STU-001", full_name="Student 001", cohort="10A"))
    session.add_all(
        [
            models.QuizQuestion(
                id="QB-MATH-001-A",
                subject_id="OL-MATH",
                concept_id="MATH-001",
                prompt="Question A",
                options_json='["A", "B", "C", "D"]',
                correct_option_index=1,
                explanation="Choose B.",
                difficulty=1,
            ),
            models.QuizQuestion(
                id="QB-MATH-001-B",
                subject_id="OL-MATH",
                concept_id="MATH-001",
                prompt="Question B",
                options_json='["A", "B", "C", "D"]',
                correct_option_index=2,
                explanation="Choose C.",
                difficulty=1,
            ),
        ]
    )
    session.commit()


def test_learning_profile_returns_lesson_cards_for_weak_concepts() -> None:
    subject_map = SubjectDiagnosisMapResponse(
        student=StudentSummary(id="STU-001", full_name="Student 001", cohort="10A"),
        subject=SubjectNode(id="OL-MATH", name="Mathematics", default_concept_id="MATH-001"),
        concepts=[
            ConceptSupportNode(
                id="MATH-001",
                subject_id="OL-MATH",
                name="Number operations",
                description="Use number operations accurately.",
                mastery_score=0.42,
                confidence=0.82,
                status="support_now",
                priority_score=0.81,
                depth=0,
                downstream_impact=3,
                evidence="Observed mastery is below the support threshold.",
            ),
            ConceptSupportNode(
                id="MATH-002",
                subject_id="OL-MATH",
                name="Ratio and proportion",
                mastery_score=0.8,
                confidence=0.9,
                status="ready",
                priority_score=0.2,
                depth=1,
                downstream_impact=1,
                evidence="Ready.",
            ),
        ],
        edges=[],
        summary=SubjectSupportSummary(total_concepts=2, support_now=1, watch=0, ready=1, missing_evidence=0),
        recommended_concept_id="MATH-001",
        explanation="Start with Number operations.",
    )

    profile = build_learning_profile(
        subject_map=subject_map,
        question_count_by_concept={"MATH-001": 2},
    )

    assert profile.lesson_cards[0].concept_id == "MATH-001"
    assert profile.recommended_quiz.concept_ids[0] == "MATH-001"
    assert profile.recommended_quiz.question_count == 2


def test_quiz_question_seed_is_idempotent(tmp_path) -> None:
    session = make_session()
    quiz_bank_path = tmp_path / "quiz_bank.json"
    quiz_bank_path.write_text(
        """
        {
          "questions": [
            {
              "id": "QB-MATH-001-A",
              "subject_id": "OL-MATH",
              "concept_id": "MATH-001",
              "prompt": "Question A",
              "options": ["A", "B", "C", "D"],
              "correct_option_index": 1,
              "explanation": "Choose B.",
              "difficulty": 1
            }
          ]
        }
        """,
        encoding="utf-8",
    )

    ensure_quiz_questions_seeded(session, quiz_bank_path)
    ensure_quiz_questions_seeded(session, quiz_bank_path)

    count = session.scalar(select(func.count(models.QuizQuestion.id)).where(models.QuizQuestion.id == "QB-MATH-001-A"))
    assert count == 1


def test_quiz_bank_is_split_by_subject_and_translated() -> None:
    quiz_dir = Path(__file__).resolve().parents[2] / "data" / "quiz"
    bank_files = sorted(path.name for path in quiz_dir.glob("*_mcq_bank.json"))
    assert bank_files == [
        "ol_english_mcq_bank.json",
        "ol_ict_mcq_bank.json",
        "ol_math_mcq_bank.json",
        "ol_science_mcq_bank.json",
    ]

    banned_fragments = [
        "It is unrelated to later lessons.",
        "It should be skipped until the final exam.",
        "It only requires guessing the answer.",
        "Choose the longest option next time.",
    ]
    for bank_file in quiz_dir.glob("*_mcq_bank.json"):
        raw = bank_file.read_text(encoding="utf-8")
        assert not any(fragment in raw for fragment in banned_fragments)
        bank = json.loads(raw)
        assert len(bank["questions"]) == 50
        for question in bank["questions"]:
            assert len(question["options"]) == 4
            if bank["subject_id"] == "OL-ENG":
                assert "prompt_si" not in question
                assert "options_si" not in question
            else:
                assert question["prompt_si"]
                assert len(question["options_si"]) == 4
                assert question["explanation_si"]


def test_start_quiz_returns_sinhala_fields_from_bank(tmp_path) -> None:
    session = make_session()
    session.add(models.Student(id="STU-001", full_name="Student 001", cohort="10A"))
    quiz_bank_path = tmp_path / "ol_math_mcq_bank.json"
    quiz_bank_path.write_text(
        """
        {
          "subject_id": "OL-MATH",
          "questions": [
            {
              "id": "QB-MATH-001-A",
              "subject_id": "OL-MATH",
              "concept_id": "MATH-001",
              "prompt": "Question A",
              "prompt_si": "සිංහල ප්‍රශ්නය A",
              "options": ["A", "B", "C", "D"],
              "options_si": ["අ", "ආ", "ඇ", "ඈ"],
              "correct_option_index": 1,
              "explanation": "Choose B.",
              "explanation_si": "ආ තෝරන්න.",
              "difficulty": 1
            }
          ]
        }
        """,
        encoding="utf-8",
    )
    ensure_quiz_questions_seeded(session, quiz_bank_path)

    attempt = start_quiz_attempt(
        session=session,
        student_id="STU-001",
        subject_id="OL-MATH",
        concept_ids=["MATH-001"],
        quiz_length=1,
        concept_names={"MATH-001": "Number operations"},
        quiz_bank_path=quiz_bank_path,
    )

    assert attempt.questions[0].prompt_si == "සිංහල ප්‍රශ්නය A"
    assert attempt.questions[0].options_si == ["අ", "ආ", "ඇ", "ඈ"]


def test_quiz_submit_creates_assessment_scores_and_variable_confidence() -> None:
    session = make_session()
    seed_quiz_data(session)
    attempt = start_quiz_attempt(
        session=session,
        student_id="STU-001",
        subject_id="OL-MATH",
        concept_ids=["MATH-001"],
        quiz_length=2,
        concept_names={"MATH-001": "Number operations"},
    )

    result = submit_quiz_attempt(
        session=session,
        attempt_id=attempt.attempt_id,
        answers={"QB-MATH-001-A": 1},
    )

    assert result.score_obtained == 1.0
    assert result.score_max == 2.0
    assert result.updated_concepts[0].mastery_score == 0.5
    assert result.updated_concepts[0].confidence == 0.5
    assert session.scalar(select(models.Assessment).where(models.Assessment.id == f"PRACTICE-{attempt.attempt_id}"))
    assert session.scalar(select(models.ConceptScore).where(models.ConceptScore.concept_id == "MATH-001")).mastery_score == 0.5
