from __future__ import annotations

from collections import defaultdict

from sqlalchemy import and_, delete, select
from sqlalchemy.orm import Session

from app.db import models


class PostgresRepository:
    def __init__(self, session: Session):
        self.session = session

    def replace_seed_data(
        self,
        *,
        students: list[models.Student],
        assessments: list[models.Assessment],
        questions: list[models.Question],
        question_results: list[models.QuestionResult],
        concept_scores: list[models.ConceptScore],
    ) -> dict:
        for table in (
            models.ConceptScore,
            models.QuestionResult,
            models.Question,
            models.Assessment,
            models.Student,
        ):
            self.session.execute(delete(table))
        self.session.add_all(students)
        self.session.add_all(assessments)
        self.session.add_all(questions)
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

    def get_student(self, student_id: str) -> dict | None:
        student = self.session.get(models.Student, student_id)
        if student is None:
            return None
        return {
            "id": student.id,
            "full_name": student.full_name,
            "cohort": student.cohort,
        }

    def list_students(self, limit: int = 250) -> list[dict]:
        rows = self.session.execute(select(models.Student).order_by(models.Student.id).limit(limit)).scalars().all()
        return [
            {
                "id": row.id,
                "full_name": row.full_name,
                "cohort": row.cohort,
            }
            for row in rows
        ]

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
