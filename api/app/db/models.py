from __future__ import annotations

from datetime import date, datetime, timezone

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.postgres import Base


def utcnow() -> datetime:
    """Naive UTC timestamp. The columns are timezone-naive; this keeps them
    unambiguously UTC without the deprecated ``datetime.utcnow``."""
    return datetime.now(timezone.utc).replace(tzinfo=None)

# ---------------------------------------------------------------------------
# School structure
# ---------------------------------------------------------------------------


class School(Base):
    """A school. ``sector`` maps directly onto the risk model's ``Sector`` variable."""

    __tablename__ = "schools"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))
    name_si: Mapped[str | None] = mapped_column(String(255), nullable=True)
    name_ta: Mapped[str | None] = mapped_column(String(255), nullable=True)
    census_no: Mapped[str | None] = mapped_column(String(32), nullable=True)
    district: Mapped[str] = mapped_column(String(64), index=True)
    province: Mapped[str] = mapped_column(String(64), index=True)
    # 'Urban' | 'Rural' | 'Estate' -- a risk model state, not free text.
    sector: Mapped[str] = mapped_column(String(16), index=True)
    school_type: Mapped[str] = mapped_column(String(64))
    medium_primary: Mapped[str] = mapped_column(String(32))

    classes: Mapped[list["ClassGroup"]] = relationship(back_populates="school")
    teachers: Mapped[list["Teacher"]] = relationship(back_populates="school")


class Teacher(Base):
    __tablename__ = "teachers"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    school_id: Mapped[str] = mapped_column(ForeignKey("schools.id"), index=True)
    full_name: Mapped[str] = mapped_column(String(255))
    full_name_si: Mapped[str | None] = mapped_column(String(255), nullable=True)
    role_title: Mapped[str] = mapped_column(String(64))
    subjects_json: Mapped[str] = mapped_column(Text, default="[]")
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)

    school: Mapped["School"] = relationship(back_populates="teachers")


class ClassGroup(Base):
    """A class such as 10A. Named ``ClassGroup`` because ``class`` is a keyword."""

    __tablename__ = "classes"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    school_id: Mapped[str] = mapped_column(ForeignKey("schools.id"), index=True)
    grade: Mapped[int] = mapped_column(Integer, index=True)
    section: Mapped[str] = mapped_column(String(8))
    medium: Mapped[str] = mapped_column(String(32))
    class_teacher_id: Mapped[str | None] = mapped_column(
        ForeignKey("teachers.id"), nullable=True
    )

    school: Mapped["School"] = relationship(back_populates="classes")
    students: Mapped[list["Student"]] = relationship(back_populates="class_group")


class Term(Base):
    __tablename__ = "terms"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    year: Mapped[int] = mapped_column(Integer, index=True)
    term_number: Mapped[int] = mapped_column(Integer)
    starts_on: Mapped[date] = mapped_column(Date)
    ends_on: Mapped[date] = mapped_column(Date)
    is_current: Mapped[bool] = mapped_column(Boolean, default=False, index=True)


# ---------------------------------------------------------------------------
# People
# ---------------------------------------------------------------------------


class Student(Base):
    __tablename__ = "students"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    full_name: Mapped[str] = mapped_column(String(255))
    full_name_si: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # Retained: existing cohort-comparison queries key on this. Mirrors "10A".
    cohort: Mapped[str] = mapped_column(String(32), index=True)

    school_id: Mapped[str | None] = mapped_column(ForeignKey("schools.id"), index=True, nullable=True)
    class_id: Mapped[str | None] = mapped_column(ForeignKey("classes.id"), index=True, nullable=True)
    admission_no: Mapped[str | None] = mapped_column(String(32), nullable=True)
    gender: Mapped[str | None] = mapped_column(String(16), nullable=True)
    date_of_birth: Mapped[date | None] = mapped_column(Date, nullable=True)
    grade: Mapped[int | None] = mapped_column(Integer, index=True, nullable=True)
    medium: Mapped[str | None] = mapped_column(String(32), nullable=True)
    guardian_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    guardian_relationship: Mapped[str | None] = mapped_column(String(64), nullable=True)
    guardian_contact: Mapped[str | None] = mapped_column(String(32), nullable=True)
    guardian_occupation: Mapped[str | None] = mapped_column(String(128), nullable=True)
    distance_to_school_km: Mapped[float | None] = mapped_column(Float, nullable=True)

    class_group: Mapped["ClassGroup"] = relationship(back_populates="students")
    assessments: Mapped[list["Assessment"]] = relationship(back_populates="student")
    concept_scores: Mapped[list["ConceptScore"]] = relationship(back_populates="student")


class User(Base):
    """Login account. Exactly one of ``student_id`` / ``teacher_id`` is set for
    non-admin roles."""

    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    username: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    # 'student' | 'teacher' | 'counsellor' | 'admin'
    role: Mapped[str] = mapped_column(String(32), index=True)
    display_name: Mapped[str] = mapped_column(String(255))
    display_name_si: Mapped[str | None] = mapped_column(String(255), nullable=True)
    locale: Mapped[str] = mapped_column(String(8), default="en")
    school_id: Mapped[str | None] = mapped_column(ForeignKey("schools.id"), index=True, nullable=True)
    student_id: Mapped[str | None] = mapped_column(ForeignKey("students.id"), nullable=True)
    teacher_id: Mapped[str | None] = mapped_column(ForeignKey("teachers.id"), nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


# ---------------------------------------------------------------------------
# Wellbeing / risk evidence
# ---------------------------------------------------------------------------


class AttendanceTerm(Base):
    __tablename__ = "attendance_terms"
    __table_args__ = (UniqueConstraint("student_id", "term_id", name="uq_attendance_student_term"),)

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"), index=True)
    term_id: Mapped[str] = mapped_column(ForeignKey("terms.id"), index=True)
    days_present: Mapped[int] = mapped_column(Integer)
    days_total: Mapped[int] = mapped_column(Integer)
    max_consecutive_absences: Mapped[int] = mapped_column(Integer, default=0)


class StudentRiskEvidence(Base):
    """One row per (student, term, risk variable).

    Shaped to mirror the Bayesian network's own evidence model: ``variable`` is a node
    name and ``state`` one of its declared states, so a row set converts straight into
    the mapping ``validate_evidence`` expects. The *absence* of a row means "not
    recorded", which is a meaningful state for the model, not missing data to impute.
    """

    __tablename__ = "student_risk_evidence"
    __table_args__ = (
        UniqueConstraint("student_id", "term_id", "variable", name="uq_evidence_student_term_var"),
    )

    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"), index=True)
    term_id: Mapped[str] = mapped_column(ForeignKey("terms.id"), index=True)
    variable: Mapped[str] = mapped_column(String(64), index=True)
    state: Mapped[str] = mapped_column(String(64))
    # 'seed' | 'teacher' | 'register' | 'derived' | 'self'
    source: Mapped[str] = mapped_column(String(16), default="seed")
    recorded_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    recorded_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)


class RiskAssessment(Base):
    """Audit record of every inference run. Required by REPORT.md section 11.2:
    who queried, for whom, on what evidence, against which parameter set."""

    __tablename__ = "risk_assessments"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"), index=True)
    term_id: Mapped[str] = mapped_column(ForeignKey("terms.id"), index=True)
    model_variant: Mapped[str] = mapped_column(String(16))
    model_fingerprint: Mapped[str] = mapped_column(String(32), index=True)
    evidence_json: Mapped[str] = mapped_column(Text)
    posterior_json: Mapped[str] = mapped_column(Text)
    p_high: Mapped[float] = mapped_column(Float, index=True)
    band: Mapped[str] = mapped_column(String(32), index=True)
    interpretation: Mapped[str] = mapped_column(String(32))
    circumstance_gap: Mapped[float] = mapped_column(Float, default=0.0)
    computed_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    computed_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)


class SupportAction(Base):
    """An *offer* of support opened against a modifiable factor.

    Every flag must lead to an offer that costs the student nothing if the flag was
    wrong (REPORT.md section 11.1). This table is how that is tracked.
    """

    __tablename__ = "support_actions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"), index=True)
    factor: Mapped[str] = mapped_column(String(64), index=True)
    action: Mapped[str] = mapped_column(Text)
    owner_role: Mapped[str] = mapped_column(String(64))
    detail: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 'offered' | 'accepted' | 'in_progress' | 'closed' | 'declined'
    status: Mapped[str] = mapped_column(String(32), default="offered", index=True)
    expected_delta: Mapped[float | None] = mapped_column(Float, nullable=True)
    opened_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    opened_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    closed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    outcome_note: Mapped[str | None] = mapped_column(Text, nullable=True)


class Alert(Base):
    """Three-tier alert hierarchy: 1 teacher in-app, 2 parent nudge, 3 counsellor review."""

    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"), index=True)
    tier: Mapped[int] = mapped_column(Integer, index=True)
    audience_role: Mapped[str] = mapped_column(String(32), index=True)
    school_id: Mapped[str | None] = mapped_column(ForeignKey("schools.id"), index=True, nullable=True)
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
    body_si: Mapped[str | None] = mapped_column(Text, nullable=True)
    # 'new' | 'ack' | 'closed'
    status: Mapped[str] = mapped_column(String(16), default="new", index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    acknowledged_by: Mapped[str | None] = mapped_column(ForeignKey("users.id"), nullable=True)
    acknowledged_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


# ---------------------------------------------------------------------------
# Academic evidence (unchanged)
# ---------------------------------------------------------------------------


class Assessment(Base):
    __tablename__ = "assessments"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"), index=True)
    assessment_date: Mapped[date] = mapped_column(Date, index=True)
    attempt_number: Mapped[int] = mapped_column(Integer)

    student: Mapped["Student"] = relationship(back_populates="assessments")
    question_results: Mapped[list["QuestionResult"]] = relationship(back_populates="assessment")
    concept_scores: Mapped[list["ConceptScore"]] = relationship(back_populates="assessment")


class Question(Base):
    __tablename__ = "questions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    concept_id: Mapped[str] = mapped_column(String(64), index=True)
    prompt: Mapped[str] = mapped_column(Text)
    score_max: Mapped[float] = mapped_column(Float)

    results: Mapped[list["QuestionResult"]] = relationship(back_populates="question")


class QuestionResult(Base):
    __tablename__ = "question_results"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    assessment_id: Mapped[str] = mapped_column(ForeignKey("assessments.id"), index=True)
    question_id: Mapped[str] = mapped_column(ForeignKey("questions.id"))
    concept_id: Mapped[str] = mapped_column(String(64), index=True)
    score_obtained: Mapped[float] = mapped_column(Float)
    score_max: Mapped[float] = mapped_column(Float)

    assessment: Mapped["Assessment"] = relationship(back_populates="question_results")
    question: Mapped["Question"] = relationship(back_populates="results")


class ConceptScore(Base):
    __tablename__ = "concept_scores"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"), index=True)
    assessment_id: Mapped[str] = mapped_column(ForeignKey("assessments.id"), index=True)
    concept_id: Mapped[str] = mapped_column(String(64), index=True)
    mastery_score: Mapped[float] = mapped_column(Float)
    confidence: Mapped[float] = mapped_column(Float)
    computed_at: Mapped[datetime] = mapped_column(DateTime)

    student: Mapped["Student"] = relationship(back_populates="concept_scores")
    assessment: Mapped["Assessment"] = relationship(back_populates="concept_scores")


class QuizQuestion(Base):
    __tablename__ = "quiz_questions"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    subject_id: Mapped[str] = mapped_column(String(64), index=True)
    concept_id: Mapped[str] = mapped_column(String(64), index=True)
    prompt: Mapped[str] = mapped_column(Text)
    options_json: Mapped[str] = mapped_column(Text)
    correct_option_index: Mapped[int] = mapped_column(Integer)
    explanation: Mapped[str] = mapped_column(Text)
    difficulty: Mapped[int] = mapped_column(Integer)


class QuizAttempt(Base):
    __tablename__ = "quiz_attempts"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    student_id: Mapped[str] = mapped_column(ForeignKey("students.id"), index=True)
    subject_id: Mapped[str] = mapped_column(String(64), index=True)
    concept_ids_json: Mapped[str] = mapped_column(Text)
    question_ids_json: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(32), index=True)
    started_at: Mapped[datetime] = mapped_column(DateTime)
    submitted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class QuizAnswer(Base):
    __tablename__ = "quiz_answers"

    id: Mapped[str] = mapped_column(String(96), primary_key=True)
    attempt_id: Mapped[str] = mapped_column(ForeignKey("quiz_attempts.id"), index=True)
    question_id: Mapped[str] = mapped_column(ForeignKey("quiz_questions.id"), index=True)
    concept_id: Mapped[str] = mapped_column(String(64), index=True)
    selected_option_index: Mapped[int | None] = mapped_column(Integer, nullable=True)
    is_correct: Mapped[int] = mapped_column(Integer)
    score_obtained: Mapped[float] = mapped_column(Float)
    score_max: Mapped[float] = mapped_column(Float)
