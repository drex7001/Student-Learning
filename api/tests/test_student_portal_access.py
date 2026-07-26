"""What a signed-in learner may and may not reach.

Both cases here are regressions. A router-level `require_staff` on the diagnosis
router locked students out of the subject list and out of their own learning map, so
the student portal could not load at all; and the learning profile advertised the
number of questions that *exist* under a name the client read as the quiz length,
which the start endpoint then rejected.
"""

from __future__ import annotations

import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app.core.deps import (
    CurrentUser,
    authorise_student_access,
    current_user,
    require_staff,
)
from app.schemas.learning import (
    DEFAULT_QUIZ_LENGTH,
    MAX_QUIZ_LENGTH,
    MIN_QUIZ_LENGTH,
    QuizStartRequest,
)

STUDENT = CurrentUser(
    id="USR-S-001",
    username="s.demo001",
    role="student",
    display_name="Demo Learner",
    student_id="STU-001",
    teacher_id=None,
    school_id="SCH-WP-001",
)


def _probe(dependency, checker=None) -> TestClient:
    app = FastAPI()

    @app.get("/probe/{student_id}")
    def probe(student_id: str, user: CurrentUser = Depends(dependency)) -> dict:
        if checker:
            checker(user, student_id)
        return {"ok": True}

    client = TestClient(app, raise_server_exceptions=False)
    client.app.dependency_overrides[current_user] = lambda: STUDENT
    return client


# -- what a learner needs to use their own portal ----------------------


def test_a_learner_may_read_curriculum_reference_data() -> None:
    """Subjects and prerequisite structure describe no learner. Blocking them leaves
    the student portal with no subject to offer."""
    assert _probe(current_user).get("/probe/ignored").status_code == 200


def test_a_learner_may_read_their_own_subject_map() -> None:
    assert (
        _probe(current_user, authorise_student_access).get("/probe/STU-001").status_code
        == 200
    )


def test_a_learner_may_not_read_another_learners_map() -> None:
    assert (
        _probe(current_user, authorise_student_access).get("/probe/STU-002").status_code
        == 403
    )


def test_a_learner_may_not_reach_cohort_wide_endpoints() -> None:
    """`/api/options` lists every student; `/api/overview/...` ranks the cohort."""
    assert _probe(require_staff).get("/probe/ignored").status_code == 403


# -- quiz length -------------------------------------------------------


def test_quiz_length_bounds_are_shared_not_duplicated() -> None:
    field = QuizStartRequest.model_fields["quiz_length"]
    limits = {type(m).__name__: getattr(m, "ge", getattr(m, "le", None)) for m in field.metadata}
    assert field.default == DEFAULT_QUIZ_LENGTH
    assert limits.get("Ge") == MIN_QUIZ_LENGTH
    assert limits.get("Le") == MAX_QUIZ_LENGTH


@pytest.mark.parametrize("length", [MIN_QUIZ_LENGTH, DEFAULT_QUIZ_LENGTH, MAX_QUIZ_LENGTH])
def test_lengths_inside_the_range_are_accepted(length: int) -> None:
    request = QuizStartRequest(student_id="STU-001", subject_id="OL-MATH", quiz_length=length)
    assert request.quiz_length == length


@pytest.mark.parametrize("length", [0, MAX_QUIZ_LENGTH + 1, 40])
def test_lengths_outside_the_range_are_rejected(length: int) -> None:
    with pytest.raises(ValueError):
        QuizStartRequest(student_id="STU-001", subject_id="OL-MATH", quiz_length=length)


def test_recommended_length_is_always_a_legal_quiz_length() -> None:
    """The profile hands the client a value it can send without validating it first.

    `question_count` is how many questions exist across the recommended concepts and
    routinely exceeds the cap; sending it as the length was the original bug.
    """
    from app.schemas.diagnosis import (
        ConceptSupportNode,
        StudentSummary,
        SubjectDiagnosisMapResponse,
        SubjectSupportSummary,
        SubjectNode,
    )
    from app.services.learning import build_learning_profile

    subject_map = SubjectDiagnosisMapResponse(
        student=StudentSummary(id="STU-001", full_name="Perera Kasun", cohort="10A"),
        subject=SubjectNode(id="OL-MATH", name="Mathematics", default_concept_id="MATH-001"),
        concepts=[
            ConceptSupportNode(
                id="MATH-001",
                subject_id="OL-MATH",
                name="Number operations",
                mastery_score=0.42,
                confidence=0.8,
                status="support_now",
                priority_score=0.81,
                depth=0,
                downstream_impact=3,
                evidence="Observed mastery is below the support threshold.",
            )
        ],
        edges=[],
        summary=SubjectSupportSummary(
            total_concepts=1, support_now=1, watch=0, ready=0, missing_evidence=0
        ),
        recommended_concept_id="MATH-001",
        explanation="Start with number operations.",
    )

    for available in (0, 1, 5, 15, 60, 300):
        profile = build_learning_profile(
            subject_map=subject_map,
            question_count_by_concept={"MATH-001": available},
        )
        length = profile.recommended_quiz.recommended_length
        assert MIN_QUIZ_LENGTH <= length <= MAX_QUIZ_LENGTH
        # And never more than actually exist, once any exist at all.
        if available:
            assert length <= max(available, MIN_QUIZ_LENGTH)
        QuizStartRequest(student_id="STU-001", subject_id="OL-MATH", quiz_length=length)
