from __future__ import annotations

from datetime import date, datetime

from sqlalchemy import Date, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.postgres import Base


class Student(Base):
    __tablename__ = "students"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    full_name: Mapped[str] = mapped_column(String(255))
    cohort: Mapped[str] = mapped_column(String(32))

    assessments: Mapped[list["Assessment"]] = relationship(back_populates="student")
    concept_scores: Mapped[list["ConceptScore"]] = relationship(back_populates="student")


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
