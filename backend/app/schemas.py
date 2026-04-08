from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field

from app.models.schemas import AssignmentStatus


class ImageRequest(BaseModel):
    image_base64: str


class SolveQuestionRequest(BaseModel):
    image_base64: str = Field(..., description="Base64-encoded question image")
    specifications: str = Field(..., description="Question selector, for example 'Question 3' or 'Section 1-2'")


class SolutionStep(BaseModel):
    idea: str = Field(default="", description="Short solving idea")
    steps: list[str] = Field(default_factory=list, description="Detailed solution steps")
    answer: str = Field(default="", description="Final answer")


class SolvedQuestion(BaseModel):
    specification: str = Field(..., description="Original selector from the teacher")
    found: bool = Field(..., description="Whether the requested question was found")
    q_number: str = Field(default="", description="Detected question number")
    content: str = Field(default="", description="Detected question content")
    question_type: str = Field(default="", description="Question category")
    knowledge_points: list[str] = Field(default_factory=list, description="Related knowledge points")
    difficulty: str = Field(default="", description="Estimated difficulty")
    solution: SolutionStep = Field(default_factory=SolutionStep, description="Structured solution")
    full_solution: str = Field(default="", description="Full solution text")
    error_message: str = Field(default="", description="Error message when the question cannot be solved")


class SolveSummary(BaseModel):
    total_specified: int = Field(..., description="Number of requested questions")
    found_count: int = Field(..., description="Number of matched questions")
    not_found: list[str] = Field(default_factory=list, description="Selectors that could not be matched")


class SolveQuestionResponse(BaseModel):
    specified_questions: list[SolvedQuestion]
    summary: SolveSummary


class QuestionResult(BaseModel):
    q_num: int
    content: str
    student_ans: str
    is_correct: bool
    score: float = Field(default=0.0, description="Awarded score")
    max_score: float = Field(default=10.0, description="Maximum score")
    analysis: str


class CorrectionResponse(BaseModel):
    questions: list[QuestionResult]


class QuestionType(str, Enum):
    image = "image"
    text = "text"


class AnswerMode(str, Enum):
    ai_generate = "ai_generate"
    teacher_submit = "teacher_submit"


class QuestionItem(BaseModel):
    type: QuestionType
    content: str = Field(..., description="Question text or Base64 image payload")
    max_score: float = Field(default=10.0, ge=0, description="Maximum score for this question")


class CreateAssignmentRequest(BaseModel):
    title: str = Field(..., min_length=1, max_length=200)
    questions: list[QuestionItem] = Field(..., min_length=1)
    submit_start_time: str | None = Field(default=None, description="ISO 8601 start time")
    submit_end_time: str | None = Field(default=None, description="ISO 8601 end time")
    appeal_end_time: str | None = Field(default=None, description="ISO 8601 appeal deadline")
    allow_resubmit: bool = Field(default=True)
    allow_late: bool = Field(default=True)
    late_score_rule: str = Field(default="100%")
    course_id: str | None = Field(default=None)


class TeacherAnswerItem(BaseModel):
    question_index: int = Field(..., ge=0)
    answer: str = Field(..., min_length=1)


class TeacherSubmitAnswersRequest(BaseModel):
    answers: list[TeacherAnswerItem] = Field(..., min_length=1)


class StandardAnswer(BaseModel):
    question_index: int
    answer: str
    source: AnswerMode


class AssignmentResponse(BaseModel):
    id: str
    title: str
    question_count: int
    total_score: float
    questions: list[QuestionItem]
    answer_mode: AnswerMode | None = None
    standard_answers: list[StandardAnswer] = Field(default_factory=list)
    created_at: str
    submit_start_time: str | None = None
    submit_end_time: str | None = None
    appeal_end_time: str | None = None
    allow_resubmit: bool = True
    allow_late: bool = True
    late_score_rule: str = "100%"
    publish_status: str = "draft"
    submitted_count: int = 0
    total_students: int = 0
    progress: str = "0/0"


class ExtendAssignmentDeadlineRequest(BaseModel):
    submit_end_time: str = Field(..., min_length=1, description="Updated submission deadline in ISO 8601 format")


class StudentSubmitRequest(BaseModel):
    student_name: str = Field(..., min_length=1, max_length=100)
    image_base64: str = Field(...)
    mime_type: str = Field(default="image/png")


class CorrectedQuestion(BaseModel):
    q_num: int = Field(..., description="Question number starting from 1")
    content: str = Field(default="")
    student_ans: str = Field(default="")
    is_correct: bool = Field(...)
    max_score: float = Field(...)
    score: float = Field(...)
    analysis: str = Field(default="")


class SubmissionResponse(BaseModel):
    submission_id: str
    assignment_id: str
    student_name: str
    image_url: str
    status: AssignmentStatus
    questions: list[CorrectedQuestion]
    total_score: float = Field(default=0.0)
    max_total_score: float = Field(default=0.0)
    error_message: str | None = None
    created_at: str
