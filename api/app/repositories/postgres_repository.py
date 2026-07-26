from __future__ import annotations

from collections import defaultdict
from datetime import datetime

from sqlalchemy import and_, delete, select
from sqlalchemy.orm import Session

from app.db import models
from app.db.models import utcnow


class PostgresRepository:
    def __init__(self, session: Session):
        self.session = session

    # -- seeding ---------------------------------------------------------

    #: Delete order is FK-safe: children before parents.
    ACADEMIC_TABLES = (
        models.QuizAnswer,
        models.QuizAttempt,
        models.QuizQuestion,
        models.ConceptScore,
        models.QuestionResult,
        models.Question,
        models.Assessment,
    )
    SCHOOL_TABLES = (
        models.Alert,
        models.SupportAction,
        models.RiskAssessment,
        models.StudentRiskEvidence,
        models.AttendanceTerm,
        models.User,
        models.Student,
        models.ClassGroup,
        models.Teacher,
        models.Term,
        models.School,
    )

    def replace_school_data(self, seed) -> dict:
        """Wipe and reseed the whole roster. Academic evidence is cleared too, because
        it is keyed on students that are about to be replaced."""
        for table in self.ACADEMIC_TABLES + self.SCHOOL_TABLES:
            self.session.execute(delete(table))
        self.session.add_all(seed.schools)
        self.session.add_all(seed.terms)
        self.session.add_all(seed.teachers)
        self.session.flush()
        self.session.add_all(seed.classes)
        self.session.flush()
        self.session.add_all(seed.students)
        self.session.flush()
        self.session.add_all(seed.users)
        self.session.add_all(seed.evidence)
        self.session.add_all(seed.attendance)
        self.session.commit()
        return {
            "school_count": self.session.query(models.School).count(),
            "class_count": self.session.query(models.ClassGroup).count(),
            "teacher_count": self.session.query(models.Teacher).count(),
            "student_count": self.session.query(models.Student).count(),
            "user_count": self.session.query(models.User).count(),
            "evidence_count": self.session.query(models.StudentRiskEvidence).count(),
        }

    def replace_academic_data(
        self,
        *,
        assessments: list[models.Assessment],
        questions: list[models.Question],
        question_results: list[models.QuestionResult],
        concept_scores: list[models.ConceptScore],
    ) -> dict:
        """Replace assessment evidence, leaving the roster and wellbeing evidence intact."""
        for table in self.ACADEMIC_TABLES:
            self.session.execute(delete(table))
        self.session.add_all(questions)
        self.session.add_all(assessments)
        self.session.flush()
        self.session.add_all(question_results)
        self.session.add_all(concept_scores)
        self.session.commit()
        return {
            "student_count": self.session.query(models.Student).count(),
            "assessment_count": self.session.query(models.Assessment).count(),
            "concept_score_count": self.session.query(models.ConceptScore).count(),
        }

    def get_latest_scores_for_student(self, student_id: str) -> dict[str, dict]:
        stmt = (
            select(models.ConceptScore, models.Assessment.assessment_date)
            .join(models.Assessment, models.Assessment.id == models.ConceptScore.assessment_id)
            .where(models.ConceptScore.student_id == student_id)
            .order_by(models.Assessment.assessment_date.desc(), models.ConceptScore.concept_id)
        )
        latest: dict[str, dict] = {}
        for concept_score, assessment_date in self.session.execute(stmt):
            if concept_score.concept_id in latest:
                continue
            latest[concept_score.concept_id] = {
                "concept_id": concept_score.concept_id,
                "mastery_score": concept_score.mastery_score,
                "confidence": concept_score.confidence,
                "assessment_date": assessment_date.isoformat(),
            }
        return latest

    # -- students --------------------------------------------------------

    @staticmethod
    def _student_dict(student: models.Student) -> dict:
        return {
            "id": student.id,
            "full_name": student.full_name,
            "full_name_si": student.full_name_si,
            "cohort": student.cohort,
            "school_id": student.school_id,
            "class_id": student.class_id,
            "grade": student.grade,
            "medium": student.medium,
            "gender": student.gender,
            "admission_no": student.admission_no,
            "guardian_name": student.guardian_name,
            "guardian_relationship": student.guardian_relationship,
            "guardian_contact": student.guardian_contact,
            "guardian_occupation": student.guardian_occupation,
            "distance_to_school_km": student.distance_to_school_km,
        }

    def get_student(self, student_id: str) -> dict | None:
        student = self.session.get(models.Student, student_id)
        if student is None:
            return None
        return self._student_dict(student)

    def list_students(
        self,
        limit: int = 250,
        *,
        school_id: str | None = None,
        class_id: str | None = None,
    ) -> list[dict]:
        stmt = select(models.Student)
        if school_id:
            stmt = stmt.where(models.Student.school_id == school_id)
        if class_id:
            stmt = stmt.where(models.Student.class_id == class_id)
        rows = (
            self.session.execute(stmt.order_by(models.Student.id).limit(limit)).scalars().all()
        )
        return [self._student_dict(row) for row in rows]

    # -- schools and classes ---------------------------------------------

    def list_schools(self) -> list[dict]:
        rows = self.session.execute(select(models.School).order_by(models.School.id)).scalars().all()
        return [
            {
                "id": row.id,
                "name": row.name,
                "name_si": row.name_si,
                "name_ta": row.name_ta,
                "district": row.district,
                "province": row.province,
                "sector": row.sector,
                "school_type": row.school_type,
                "medium_primary": row.medium_primary,
            }
            for row in rows
        ]

    def list_classes(self, school_id: str | None = None) -> list[dict]:
        stmt = select(models.ClassGroup)
        if school_id:
            stmt = stmt.where(models.ClassGroup.school_id == school_id)
        rows = (
            self.session.execute(
                stmt.order_by(models.ClassGroup.school_id, models.ClassGroup.grade, models.ClassGroup.section)
            )
            .scalars()
            .all()
        )
        return [
            {
                "id": row.id,
                "school_id": row.school_id,
                "grade": row.grade,
                "section": row.section,
                "label": f"{row.grade}{row.section}",
                "medium": row.medium,
                "class_teacher_id": row.class_teacher_id,
            }
            for row in rows
        ]

    # -- terms, attendance, risk evidence --------------------------------

    def get_current_term(self) -> models.Term | None:
        return (
            self.session.execute(
                select(models.Term).where(models.Term.is_current.is_(True)).limit(1)
            )
            .scalars()
            .first()
        )

    def get_risk_evidence(self, student_id: str, term_id: str) -> dict[str, dict]:
        rows = (
            self.session.execute(
                select(models.StudentRiskEvidence).where(
                    and_(
                        models.StudentRiskEvidence.student_id == student_id,
                        models.StudentRiskEvidence.term_id == term_id,
                    )
                )
            )
            .scalars()
            .all()
        )
        return {
            row.variable: {
                "state": row.state,
                "source": row.source,
                "recorded_at": row.recorded_at.isoformat() if row.recorded_at else None,
                "note": row.note,
            }
            for row in rows
        }

    def get_risk_evidence_bulk(
        self, student_ids: list[str], term_id: str
    ) -> dict[str, dict[str, str]]:
        if not student_ids:
            return {}
        rows = (
            self.session.execute(
                select(models.StudentRiskEvidence).where(
                    and_(
                        models.StudentRiskEvidence.student_id.in_(student_ids),
                        models.StudentRiskEvidence.term_id == term_id,
                    )
                )
            )
            .scalars()
            .all()
        )
        evidence: dict[str, dict[str, str]] = defaultdict(dict)
        for row in rows:
            evidence[row.student_id][row.variable] = row.state
        return dict(evidence)

    def upsert_risk_evidence(
        self,
        *,
        student_id: str,
        term_id: str,
        variable: str,
        state: str | None,
        source: str,
        recorded_by: str | None,
        note: str | None = None,
    ) -> None:
        """``state=None`` deletes the row -- "not recorded" is the absence of evidence,
        not a state to store."""
        existing = (
            self.session.execute(
                select(models.StudentRiskEvidence).where(
                    and_(
                        models.StudentRiskEvidence.student_id == student_id,
                        models.StudentRiskEvidence.term_id == term_id,
                        models.StudentRiskEvidence.variable == variable,
                    )
                )
            )
            .scalars()
            .first()
        )
        if state is None:
            if existing is not None:
                self.session.delete(existing)
            return
        if existing is None:
            self.session.add(
                models.StudentRiskEvidence(
                    id=f"EV-{student_id}-{term_id}-{variable}"[:96],
                    student_id=student_id,
                    term_id=term_id,
                    variable=variable,
                    state=state,
                    source=source,
                    recorded_by=recorded_by,
                    recorded_at=utcnow(),
                    note=note,
                )
            )
            return
        existing.state = state
        existing.source = source
        existing.recorded_by = recorded_by
        existing.recorded_at = utcnow()
        existing.note = note

    def get_attendance(self, student_id: str) -> list[dict]:
        rows = (
            self.session.execute(
                select(models.AttendanceTerm, models.Term)
                .join(models.Term, models.Term.id == models.AttendanceTerm.term_id)
                .where(models.AttendanceTerm.student_id == student_id)
                .order_by(models.Term.year, models.Term.term_number)
            )
            .all()
        )
        return [
            {
                "term_id": term.id,
                "term_label": f"{term.year} Term {term.term_number}",
                "days_present": attendance.days_present,
                "days_total": attendance.days_total,
                "rate": round(attendance.days_present / max(attendance.days_total, 1), 4),
                "max_consecutive_absences": attendance.max_consecutive_absences,
            }
            for attendance, term in rows
        ]

    def latest_scores_by_student(self) -> dict[str, dict[str, float]]:
        """Every learner's latest score per concept, in one pass."""
        stmt = (
            select(
                models.ConceptScore.student_id,
                models.ConceptScore.concept_id,
                models.ConceptScore.mastery_score,
                models.Assessment.assessment_date,
            )
            .join(models.Assessment, models.Assessment.id == models.ConceptScore.assessment_id)
            .order_by(
                models.ConceptScore.student_id,
                models.ConceptScore.concept_id,
                models.Assessment.assessment_date.desc(),
            )
        )
        latest: dict[str, dict[str, float]] = defaultdict(dict)
        for student_id, concept_id, mastery, _date in self.session.execute(stmt):
            if concept_id in latest[student_id]:
                continue
            latest[student_id][concept_id] = mastery
        return dict(latest)

    def average_mastery_by_student(self) -> dict[str, float]:
        """Mean of each learner's latest score per concept, across all subjects."""
        stmt = (
            select(
                models.ConceptScore.student_id,
                models.ConceptScore.concept_id,
                models.ConceptScore.mastery_score,
                models.Assessment.assessment_date,
            )
            .join(models.Assessment, models.Assessment.id == models.ConceptScore.assessment_id)
            .order_by(
                models.ConceptScore.student_id,
                models.ConceptScore.concept_id,
                models.Assessment.assessment_date.desc(),
            )
        )
        latest: dict[str, dict[str, float]] = defaultdict(dict)
        for student_id, concept_id, mastery, _date in self.session.execute(stmt):
            if concept_id in latest[student_id]:
                continue
            latest[student_id][concept_id] = mastery
        return {
            student_id: round(sum(scores.values()) / len(scores), 4)
            for student_id, scores in latest.items()
            if scores
        }

    def get_student_assessment_summary(self, student_id: str) -> dict:
        assessments = self.session.execute(
            select(models.Assessment)
            .where(models.Assessment.student_id == student_id)
            .order_by(models.Assessment.assessment_date.desc())
        ).scalars().all()
        latest_assessment = assessments[0].assessment_date.isoformat() if assessments else None
        return {
            "assessment_count": len(assessments),
            "latest_assessment_date": latest_assessment,
        }

    def get_recent_scores_for_student(
        self,
        student_id: str,
        concept_ids: list[str],
        limit_per_concept: int = 3,
    ) -> dict[str, list[dict]]:
        if not concept_ids:
            return {}

        stmt = (
            select(models.ConceptScore, models.Assessment.assessment_date)
            .join(models.Assessment, models.Assessment.id == models.ConceptScore.assessment_id)
            .where(
                and_(
                    models.ConceptScore.student_id == student_id,
                    models.ConceptScore.concept_id.in_(concept_ids),
                )
            )
            .order_by(
                models.ConceptScore.concept_id,
                models.Assessment.assessment_date.desc(),
                models.ConceptScore.computed_at.desc(),
            )
        )

        scores_by_concept: dict[str, list[dict]] = defaultdict(list)
        for concept_score, assessment_date in self.session.execute(stmt):
            concept_scores = scores_by_concept[concept_score.concept_id]
            if len(concept_scores) >= limit_per_concept:
                continue
            concept_scores.append(
                {
                    "assessment_date": assessment_date.isoformat(),
                    "mastery_score": concept_score.mastery_score,
                    "confidence": concept_score.confidence,
                }
            )
        return dict(scores_by_concept)

    def get_latest_cohort_mastery(self, cohort: str, concept_id: str) -> float | None:
        stmt = (
            select(models.Student.id, models.ConceptScore.mastery_score, models.Assessment.assessment_date)
            .join(models.Assessment, models.Assessment.student_id == models.Student.id)
            .join(
                models.ConceptScore,
                and_(
                    models.ConceptScore.assessment_id == models.Assessment.id,
                    models.ConceptScore.student_id == models.Student.id,
                    models.ConceptScore.concept_id == concept_id,
                ),
            )
            .where(models.Student.cohort == cohort)
            .order_by(models.Student.id, models.Assessment.assessment_date.desc(), models.ConceptScore.computed_at.desc())
        )

        latest_by_student: dict[str, float] = {}
        for student_id, mastery_score, _assessment_date in self.session.execute(stmt):
            if student_id in latest_by_student:
                continue
            latest_by_student[student_id] = mastery_score

        if not latest_by_student:
            return None
        return round(sum(latest_by_student.values()) / len(latest_by_student), 4)
