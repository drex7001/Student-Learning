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


#: Bounds for a practice quiz. Named so the schema and the profile agree instead of
#: each carrying its own magic number.
MIN_QUIZ_LENGTH = 1
MAX_QUIZ_LENGTH = 12
DEFAULT_QUIZ_LENGTH = 8


class RecommendedQuiz(BaseModel):
    concept_ids: list[str]
    #: How many questions exist for these concepts -- what to *show* the learner.
    question_count: int
    #: How many to actually ask, already inside the allowed range -- what to *send*
    #: to `/api/learn/quiz/start`. These were previously one field, and passing the
    #: available total as the length failed validation.
    recommended_length: int
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
    quiz_length: int = Field(
        default=DEFAULT_QUIZ_LENGTH, ge=MIN_QUIZ_LENGTH, le=MAX_QUIZ_LENGTH
    )


class QuizQuestionItem(BaseModel):
    id: str
    concept_id: str
    concept_name: str
    prompt: str
    prompt_si: str | None = None
    options: list[str]
    options_si: list[str] | None = None
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
    prompt_si: str | None = None
    selected_option_index: int | None
    correct_option_index: int
    is_correct: bool
    score_obtained: float
    score_max: float
    explanation: str
    explanation_si: str | None = None


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
