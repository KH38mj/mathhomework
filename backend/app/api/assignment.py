from __future__ import annotations

import base64
import logging
import traceback
import uuid
from datetime import datetime

from fastapi import APIRouter, BackgroundTasks, Depends, File, Header, HTTPException, UploadFile

from app.config import settings
from app.models.schemas import AssignmentStatus
from app.schemas import (
    AnswerMode,
    AssignmentResponse,
    CorrectedQuestion,
    CreateAssignmentRequest,
    ExtendAssignmentDeadlineRequest,
    QuestionType,
    StandardAnswer,
    SubmissionResponse,
    TeacherSubmitAnswersRequest,
)
from app.services.ai_service import AIServiceError, call_text, call_vision, call_vision_with_refinement
from app.services.prompts import (
    GENERATE_ANSWER_PROMPT_IMAGE,
    GENERATE_ANSWER_PROMPT_TEXT,
    GENERATE_ANSWER_SYSTEM,
)
from app.services.roster_service import get_course_student_count
from app.services.storage_service import StorageService, get_storage_service
from app.storage import (
    Assignment,
    Submission,
    StudentSession,
    get_assignment,
    get_latest_submission_for_student,
    get_student_session,
    get_submission,
    is_admin_session_valid,
    list_assignments,
    list_submissions_by_assignment,
    save_assignment,
    save_submission,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/assignments", tags=["assignments"])


@router.post("", response_model=AssignmentResponse, status_code=201)
async def create_assignment(req: CreateAssignmentRequest):
    for index, question in enumerate(req.questions, start=1):
        if question.type != QuestionType.image:
            continue
        try:
            raw = base64.b64decode(question.content)
        except Exception as exc:  # pragma: no cover - defensive surface
            raise HTTPException(status_code=400, detail=f"Question {index} has invalid Base64 image content") from exc
        if len(raw) > settings.MAX_IMAGE_SIZE_MB * 1024 * 1024:
            raise HTTPException(
                status_code=400,
                detail=f"Question {index} exceeds the {settings.MAX_IMAGE_SIZE_MB}MB image size limit",
            )

    assignment = Assignment(
        id=uuid.uuid4().hex[:12],
        title=req.title,
        questions=req.questions,
        submit_start_time=req.submit_start_time,
        submit_end_time=req.submit_end_time,
        appeal_end_time=req.appeal_end_time,
        allow_resubmit=req.allow_resubmit,
        allow_late=req.allow_late,
        late_score_rule=req.late_score_rule,
        course_id=req.course_id,
        publish_status="published" if req.submit_start_time else "draft",
    )
    save_assignment(assignment)
    return _to_response(assignment)


@router.get("", response_model=list[AssignmentResponse])
async def get_assignments():
    return [_to_response(item) for item in list_assignments()]


@router.get("/{assignment_id}", response_model=AssignmentResponse)
async def get_assignment_detail(assignment_id: str):
    return _to_response(_get_or_404(assignment_id))


@router.post("/{assignment_id}/answers/ai-generate", response_model=AssignmentResponse)
async def ai_generate_answers(assignment_id: str):
    assignment = _get_or_404(assignment_id)
    if assignment.standard_answers:
        raise HTTPException(status_code=409, detail="This assignment already has standard answers")
    if not settings.AI_VISION_API_KEY:
        raise HTTPException(status_code=503, detail="The vision model is not configured")

    answers: list[StandardAnswer] = []
    for index, question in enumerate(assignment.questions):
        try:
            if question.type == QuestionType.image:
                result = await call_vision(
                    image_base64=question.content,
                    prompt=GENERATE_ANSWER_PROMPT_IMAGE,
                    system_prompt=GENERATE_ANSWER_SYSTEM,
                )
            else:
                result = await call_text(
                    prompt=GENERATE_ANSWER_PROMPT_TEXT.format(content=question.content),
                    system_prompt=GENERATE_ANSWER_SYSTEM,
                )
            answer_text = result.get("answer", "")
            key_result = result.get("key_result", "")
            full_answer = f"{answer_text}\n\n**Final Result:** {key_result}" if key_result else answer_text
        except AIServiceError as exc:
            logger.warning("Question %s answer generation failed: %s", index + 1, exc)
            full_answer = f"[AI generation failed] {exc}"

        answers.append(
            StandardAnswer(
                question_index=index,
                answer=full_answer,
                source=AnswerMode.ai_generate,
            )
        )

    assignment.answer_mode = AnswerMode.ai_generate
    assignment.standard_answers = answers
    save_assignment(assignment)
    return _to_response(assignment)


@router.post("/{assignment_id}/answers/teacher-submit", response_model=AssignmentResponse)
async def teacher_submit_answers(assignment_id: str, req: TeacherSubmitAnswersRequest):
    assignment = _get_or_404(assignment_id)
    if assignment.standard_answers:
        raise HTTPException(status_code=409, detail="This assignment already has standard answers")

    question_count = len(assignment.questions)
    for answer in req.answers:
        if answer.question_index >= question_count:
            raise HTTPException(
                status_code=400,
                detail=f"Question index {answer.question_index} is out of range for {question_count} questions",
            )

    assignment.answer_mode = AnswerMode.teacher_submit
    assignment.standard_answers = [
        StandardAnswer(
            question_index=item.question_index,
            answer=item.answer,
            source=AnswerMode.teacher_submit,
        )
        for item in req.answers
    ]
    save_assignment(assignment)
    return _to_response(assignment)


@router.post("/{assignment_id}/extend", response_model=AssignmentResponse)
async def extend_assignment_deadline(
    assignment_id: str,
    req: ExtendAssignmentDeadlineRequest,
):
    assignment = _get_or_404(assignment_id)
    assignment.submit_end_time = req.submit_end_time
    save_assignment(assignment)
    return _to_response(assignment)


@router.post("/{assignment_id}/submit", response_model=SubmissionResponse, status_code=202)
async def student_submit_upload(
    assignment_id: str,
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    x_student_token: str = Header(..., description="Student session token"),
    storage: StorageService = Depends(get_storage_service),
):
    assignment = _get_or_404(assignment_id)
    student_session = _require_student_session(x_student_token)

    if not assignment.standard_answers:
        raise HTTPException(status_code=409, detail="This assignment cannot be graded until standard answers are set")
    if not settings.AI_VISION_API_KEY:
        raise HTTPException(status_code=503, detail="The vision model is not configured")
    if file.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(status_code=400, detail="Only JPEG, PNG, and WebP images are supported")

    contents = await file.read()
    if len(contents) > settings.MAX_IMAGE_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"Image size cannot exceed {settings.MAX_IMAGE_SIZE_MB}MB")
    await file.seek(0)

    previous = get_latest_submission_for_student(assignment_id, student_session.student_id)
    is_late = _validate_submission_window(assignment, previous)
    submission = Submission(
        id=uuid.uuid4().hex[:12],
        assignment_id=assignment_id,
        student_id=student_session.student_id,
        student_name=student_session.display_name,
        status=AssignmentStatus.processing,
        max_total_score=sum(question.max_score for question in assignment.questions),
        resubmit_count=(previous.resubmit_count + 1) if previous else 0,
        is_late=is_late,
    )
    submission.image_url = await storage.upload_image(file)
    save_submission(submission)

    background_tasks.add_task(
        _process_correction_task,
        submission_id=submission.id,
        assignment=assignment,
        image_url=submission.image_url,
        mime_type=file.content_type or "image/png",
        storage=storage,
    )
    return _to_submission_response(submission)


@router.get("/{assignment_id}/submissions/me", response_model=SubmissionResponse)
async def get_my_submission(
    assignment_id: str,
    x_student_token: str = Header(..., description="Student session token"),
):
    _get_or_404(assignment_id)
    student_session = _require_student_session(x_student_token)
    submission = get_latest_submission_for_student(assignment_id, student_session.student_id)
    if not submission:
        raise HTTPException(status_code=404, detail="No submission exists for the current student")
    return _to_submission_response(submission)


@router.get("/{assignment_id}/submissions/{submission_id}", response_model=SubmissionResponse)
async def get_submission_status(
    assignment_id: str,
    submission_id: str,
    x_student_token: str | None = Header(default=None, description="Student session token"),
    x_admin_token: str | None = Header(default=None, description="Admin session token"),
):
    _get_or_404(assignment_id)
    submission = get_submission(submission_id)
    if not submission or submission.assignment_id != assignment_id:
        raise HTTPException(status_code=404, detail="Submission not found")

    if x_admin_token and is_admin_session_valid(x_admin_token):
        return _to_submission_response(submission)

    student_session = _require_student_session(x_student_token)
    if submission.student_id != student_session.student_id:
        raise HTTPException(status_code=403, detail="You are not allowed to access this submission")
    return _to_submission_response(submission)


@router.get("/{assignment_id}/submissions", response_model=list[SubmissionResponse])
async def get_submissions(
    assignment_id: str,
    x_admin_token: str = Header(..., description="Admin session token"),
):
    _get_or_404(assignment_id)
    if not is_admin_session_valid(x_admin_token):
        raise HTTPException(status_code=401, detail="Admin session is invalid or expired")
    return [_to_submission_response(item) for item in list_submissions_by_assignment(assignment_id)]


async def _process_correction_task(
    submission_id: str,
    assignment: Assignment,
    image_url: str,
    mime_type: str,
    storage: StorageService,
):
    submission = get_submission(submission_id)
    if not submission:
        logger.error("Could not start grading task for missing submission %s", submission_id)
        return

    try:
        image_base64 = await storage.get_image_base64(image_url)
        answers_text = _build_answers_text(assignment)
        result = await call_vision_with_refinement(
            image_base64=image_base64,
            standard_answers=answers_text,
            mime_type=mime_type,
        )
        corrected = _parse_correction(result, assignment)

        submission.corrected_questions = corrected
        submission.total_score = sum(question.score for question in corrected)
        submission.status = AssignmentStatus.completed
        submission.submit_status = "graded"
    except AIServiceError as exc:
        logger.error("Grading task %s failed in AI service: %s", submission_id, exc)
        submission.status = AssignmentStatus.failed
        submission.error_message = f"AI service error: {exc}"
    except Exception as exc:  # pragma: no cover - defensive surface
        logger.error("Grading task %s crashed:\n%s", submission_id, traceback.format_exc())
        submission.status = AssignmentStatus.failed
        submission.error_message = f"Internal server error: {exc}"
    finally:
        save_submission(submission)


def _require_student_session(session_token: str | None) -> StudentSession:
    if not session_token:
        raise HTTPException(status_code=401, detail="Missing student session token")
    session = get_student_session(session_token)
    if not session:
        raise HTTPException(status_code=401, detail="Student session is invalid or expired")
    return session


def _to_submission_response(submission: Submission) -> SubmissionResponse:
    return SubmissionResponse(
        submission_id=submission.id,
        assignment_id=submission.assignment_id,
        student_name=submission.student_name,
        image_url=submission.image_url,
        status=submission.status,
        questions=submission.corrected_questions,
        total_score=submission.total_score,
        max_total_score=submission.max_total_score,
        error_message=submission.error_message,
        created_at=submission.created_at,
    )


def _get_or_404(assignment_id: str) -> Assignment:
    assignment = get_assignment(assignment_id)
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return assignment


def _to_response(assignment: Assignment) -> AssignmentResponse:
    submissions = list_submissions_by_assignment(assignment.id)
    submitted_count = len({item.student_id for item in submissions})
    total_students = get_course_student_count(assignment.course_id)
    progress = f"{submitted_count}/{total_students}" if total_students else f"{submitted_count}/0"

    return AssignmentResponse(
        id=assignment.id,
        title=assignment.title,
        question_count=len(assignment.questions),
        total_score=sum(question.max_score for question in assignment.questions),
        questions=assignment.questions,
        answer_mode=assignment.answer_mode,
        standard_answers=[],
        created_at=assignment.created_at,
        submit_start_time=assignment.submit_start_time,
        submit_end_time=assignment.submit_end_time,
        appeal_end_time=assignment.appeal_end_time,
        allow_resubmit=assignment.allow_resubmit,
        allow_late=assignment.allow_late,
        late_score_rule=assignment.late_score_rule,
        publish_status=assignment.publish_status,
        submitted_count=submitted_count,
        total_students=total_students,
        progress=progress,
    )


def _build_answers_text(assignment: Assignment) -> str:
    answer_map = {item.question_index: item.answer for item in assignment.standard_answers}
    lines: list[str] = []
    for index, question in enumerate(assignment.questions):
        answer = answer_map.get(index, "(No standard answer)")
        lines.append(f"Question {index + 1} (max {question.max_score}):\n{answer}")
    return "\n\n".join(lines)


def _parse_correction(result: dict, assignment: Assignment) -> list[CorrectedQuestion]:
    max_scores = {index + 1: question.max_score for index, question in enumerate(assignment.questions)}
    corrected: list[CorrectedQuestion] = []

    for index, item in enumerate(result.get("questions", []), start=1):
        q_num = int(item.get("q_num", index) or index)
        max_score = max_scores.get(q_num, 10.0)
        try:
            raw_score = float(item.get("score", 0) or 0)
        except (TypeError, ValueError):
            raw_score = 0.0
        score = max(0.0, min(raw_score, max_score))

        corrected.append(
            CorrectedQuestion(
                q_num=q_num,
                content=item.get("content", ""),
                student_ans=item.get("student_ans", ""),
                is_correct=bool(item.get("is_correct", False)),
                max_score=max_score,
                score=score,
                analysis=item.get("analysis", ""),
            )
        )

    return corrected


def _parse_iso_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def _validate_submission_window(assignment: Assignment, previous: Submission | None) -> bool:
    now = datetime.now()
    start_time = _parse_iso_datetime(assignment.submit_start_time)
    end_time = _parse_iso_datetime(assignment.submit_end_time)

    if assignment.publish_status != "published":
        raise HTTPException(status_code=409, detail="This assignment has not been published yet")
    if start_time and now < start_time:
        raise HTTPException(status_code=409, detail="This assignment is not open for submission yet")
    if previous and not assignment.allow_resubmit:
        raise HTTPException(status_code=409, detail="This assignment does not allow resubmission")
    if end_time and now > end_time and not assignment.allow_late:
        raise HTTPException(status_code=409, detail="This assignment is already past the submission deadline")
    return bool(end_time and now > end_time)
