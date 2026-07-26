"""Access-control tests.

These cover the rules that a hidden button cannot enforce: a student may read only
their own learning record, no student may reach the risk endpoints at all, and the
seeding endpoints are administrator-only.
"""

from __future__ import annotations

import pytest
from fastapi import Depends, FastAPI, HTTPException
from fastapi.testclient import TestClient

from app.core.deps import (
    CurrentUser,
    authorise_student_access,
    current_user,
    deny_students,
    require_admin,
    require_role,
    require_staff,
)
from app.core.security import (
    SESSION_COOKIE,
    create_session_token,
    decode_session_token,
    hash_password,
    verify_password,
)


def make_user(role: str, student_id: str | None = None) -> CurrentUser:
    return CurrentUser(
        id=f"USR-{role}",
        username=role,
        role=role,
        display_name=role.title(),
        student_id=student_id,
        teacher_id=None if role == "student" else "TCH-001",
        school_id="SCH-WP-001",
    )


# -- password hashing --------------------------------------------------


def test_password_round_trip() -> None:
    digest = hash_password("wellbeing2026")
    assert digest != "wellbeing2026"
    assert verify_password("wellbeing2026", digest)
    assert not verify_password("wrong", digest)


def test_verify_password_survives_a_corrupt_hash() -> None:
    assert verify_password("anything", "not-a-bcrypt-hash") is False


# -- tokens ------------------------------------------------------------


def test_session_token_round_trip() -> None:
    token = create_session_token(
        user_id="USR-1", username="t.demo", role="teacher", teacher_id="TCH-1"
    )
    claims = decode_session_token(token)
    assert claims is not None
    assert claims["sub"] == "USR-1"
    assert claims["role"] == "teacher"
    assert claims["teacher_id"] == "TCH-1"


def test_tampered_token_is_rejected() -> None:
    token = create_session_token(user_id="USR-1", username="x", role="admin")
    assert decode_session_token(token + "x") is None
    assert decode_session_token("garbage") is None


# -- the rule that matters most ----------------------------------------


def test_students_cannot_reach_risk_information() -> None:
    """A flag must cost the student nothing if it was wrong. Telling a child the model
    expects them to leave school is a cost."""
    with pytest.raises(HTTPException) as excinfo:
        deny_students(make_user("student", student_id="STU-001"))
    assert excinfo.value.status_code == 403

    for role in ("teacher", "counsellor", "admin"):
        deny_students(make_user(role))  # must not raise


def test_a_student_may_read_only_their_own_record() -> None:
    student = make_user("student", student_id="STU-001")
    authorise_student_access(student, "STU-001")  # own record: allowed

    with pytest.raises(HTTPException) as excinfo:
        authorise_student_access(student, "STU-002")
    assert excinfo.value.status_code == 403


def test_staff_may_read_any_learner() -> None:
    for role in ("teacher", "counsellor", "admin"):
        authorise_student_access(make_user(role), "STU-999")


def test_a_student_account_with_no_linked_learner_is_refused() -> None:
    orphan = make_user("student", student_id=None)
    with pytest.raises(HTTPException):
        authorise_student_access(orphan, "STU-001")


# -- role dependencies -------------------------------------------------


def _client_for(dependency) -> TestClient:
    app = FastAPI()

    @app.get("/probe")
    def probe(user: CurrentUser = Depends(dependency)) -> dict:
        return {"role": user.role}

    return TestClient(app, raise_server_exceptions=False)


@pytest.mark.parametrize(
    ("dependency", "allowed", "denied"),
    [
        (require_staff, ("teacher", "counsellor", "admin"), ("student",)),
        (require_admin, ("admin",), ("teacher", "counsellor", "student")),
        (require_role("counsellor"), ("counsellor",), ("teacher", "admin", "student")),
    ],
)
def test_role_dependencies(dependency, allowed, denied, monkeypatch) -> None:
    for role in allowed:
        app_client = _client_for(dependency)
        app_client.app.dependency_overrides[current_user] = lambda role=role: make_user(role)
        assert app_client.get("/probe").status_code == 200
    for role in denied:
        app_client = _client_for(dependency)
        app_client.app.dependency_overrides[current_user] = lambda role=role: make_user(role)
        assert app_client.get("/probe").status_code == 403


def test_missing_cookie_is_unauthorised() -> None:
    app = FastAPI()

    @app.get("/probe")
    def probe(user: CurrentUser = Depends(require_staff)) -> dict:
        return {"ok": True}

    client = TestClient(app, raise_server_exceptions=False)
    assert client.get("/probe").status_code == 401


def test_session_cookie_name_is_stable() -> None:
    """The frontend proxy and the logout route both depend on this name."""
    assert SESSION_COOKIE == "wellbeing_session"
