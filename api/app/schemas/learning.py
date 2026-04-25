from __future__ import annotations

from pydantic import BaseModel, Field

from app.schemas.diagnosis import ConceptSupportNode, StudentSummary, SubjectNode, SubjectSupportSummary


class LessonCard(BaseModel):
    concept_id: str
    concept_name: str
    concept_name_si: str | None = None
    status: str
    mastery_score: float | None = None
    confidence: float
    priority_score: float
    why_it_matters: str
    study_tips: list[str]


class RecommendedQuiz(BaseModel):
    concept_ids: list[str]
    question_count: int
    reason: str


class LearningProfileResponse(BaseModel):
    student: StudentSummary
    subject: SubjectNode
    summary: SubjectSupportSummary
    recommended_concepts: list[ConceptSupportNode]
    lesson_cards: list[LessonCard]
    recommended_quiz: RecommendedQuiz


class QuizStartRequest(BaseModel):
    student_id: str
    subject_id: str
    concept_ids: list[str] | None = None
    quiz_length: int = Field(default=8, ge=1, le=12)


class QuizQuestionItem(BaseModel):
    id: str
    concept_id: str
    concept_name: str
    prompt: str
    options: list[str]
    difficulty: int


class QuizAttemptResponse(BaseModel):
    attempt_id: str
    student_id: str
    subject_id: str
    concept_ids: list[str]
    status: str
    questions: list[QuizQuestionItem]


class QuizSubmittedAnswer(BaseModel):
    question_id: str
    selected_option_index: int | None = None


class QuizSubmitRequest(BaseModel):
    answers: list[QuizSubmittedAnswer]


class QuizAnswerResult(BaseModel):
    question_id: str
    concept_id: str
    prompt: str
    selected_option_index: int | None
    correct_option_index: int
    is_correct: bool
    score_obtained: float
    score_max: float
    explanation: str


class UpdatedConceptScore(BaseModel):
    concept_id: str
    mastery_score: float
    confidence: float
    answered_question_count: int
    mapped_question_count: int


class QuizSubmitResponse(BaseModel):
    attempt_id: str
    status: str
    score_obtained: float
    score_max: float
    percentage: float
    results: list[QuizAnswerResult]
    updated_concepts: list[UpdatedConceptScore]
