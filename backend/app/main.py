import base64
import logging

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.schemas import (
    ImageRequest, CorrectionResponse, QuestionResult,
    SolveQuestionRequest, SolveQuestionResponse, SolvedQuestion,
    SolutionStep, SolveSummary
)
from app.config import MAX_IMAGE_SIZE_MB, settings
from app.api.assignment import router as assignment_router
from app.api.course import router as course_router
from app.api.admin import router as admin_router
from app.api.student import router as student_router
from app.services.ai_service import call_vision_with_refinement, call_solve_questions, AIServiceError
from app.storage import mark_processing_submissions_failed

logger = logging.getLogger(__name__)

app = FastAPI(title="AI 数学作业批改服务", version="0.1.0")
app.include_router(assignment_router)
app.include_router(course_router)
app.include_router(admin_router)
app.include_router(student_router)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    return {"status": "ok"}


@app.on_event("startup")
async def recover_processing_submissions():
    recovered = mark_processing_submissions_failed(
        "The service restarted before grading finished. Please resubmit the assignment."
    )
    if recovered:
        logger.warning("Marked %s stale processing submissions as failed on startup", recovered)


@app.post("/api/v1/correct/upload", response_model=CorrectionResponse)
async def correct_by_upload(file: UploadFile = File(...)):
    """【测试接口】直接上传作业图片，AI 自动识别题目并批改。

    无需预创建作业，适合前端快速测试 AI 批改能力。
    """
    print(f"\n>>> 收到上传请求: {file.filename}, content_type={file.content_type}")

    if file.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(status_code=400, detail="仅支持 JPEG / PNG / WebP 格式的图片")

    if not settings.AI_VISION_API_KEY or not settings.AI_TEXT_API_KEY:
        raise HTTPException(status_code=503, detail="AI 服务未配置，请先设置 API Key")

    contents = await file.read()
    if len(contents) > MAX_IMAGE_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"图片大小不能超过 {MAX_IMAGE_SIZE_MB}MB")

    image_base64 = base64.b64encode(contents).decode("utf-8")

    try:
        result = await call_vision_with_refinement(
            image_base64=image_base64,
            mime_type=file.content_type or "image/png",
        )

        # 解析 AI 返回的 JSON
        questions = result.get("questions", [])
        corrected = [
            QuestionResult(
                q_num=q.get("q_num", i + 1),
                content=q.get("content", ""),
                student_ans=q.get("student_ans", ""),
                is_correct=q.get("is_correct", False),
                score=q.get("score", 0),
                max_score=q.get("max_score", 10),
                analysis=q.get("analysis", ""),
            )
            for i, q in enumerate(questions)
        ]

        return CorrectionResponse(questions=corrected)

    except AIServiceError as exc:
        logger.error("AI 批改失败: %s", exc)
        raise HTTPException(
            status_code=422,
            detail={
                "error": "AI 返回数据解析失败",
                "message": str(exc),
                "hint": "可能是 LaTeX 公式转义错误，请重试或联系管理员"
            }
        )
    except Exception as exc:
        logger.exception("未知错误")
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {exc}")


@app.post("/api/v1/correct/base64", response_model=CorrectionResponse)
async def correct_by_base64(req: ImageRequest):
    """【测试接口】通过 Base64 字符串接收图片，AI 自动识别题目并批改。

    适配小程序端直接传 Base64 的场景，无需预创建作业。
    """
    try:
        image_data = base64.b64decode(req.image_base64)
    except Exception:
        raise HTTPException(status_code=400, detail="无效的 Base64 编码")

    if len(image_data) > MAX_IMAGE_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"图片大小不能超过 {MAX_IMAGE_SIZE_MB}MB")

    if not settings.AI_VISION_API_KEY or not settings.AI_TEXT_API_KEY:
        raise HTTPException(status_code=503, detail="AI 服务未配置，请先设置 API Key")

    try:
        result = await call_vision_with_refinement(
            image_base64=req.image_base64,
            mime_type="image/png",
        )

        # 解析 AI 返回的 JSON
        questions = result.get("questions", [])
        corrected = [
            QuestionResult(
                q_num=q.get("q_num", i + 1),
                content=q.get("content", ""),
                student_ans=q.get("student_ans", ""),
                is_correct=q.get("is_correct", False),
                score=q.get("score", 0),
                max_score=q.get("max_score", 10),
                analysis=q.get("analysis", ""),
            )
            for i, q in enumerate(questions)
        ]

        return CorrectionResponse(questions=corrected)

    except AIServiceError as exc:
        logger.error("AI 批改失败: %s", exc)
        raise HTTPException(
            status_code=422,
            detail={
                "error": "AI 返回数据解析失败",
                "message": str(exc),
                "hint": "可能是 LaTeX 公式转义错误，请重试或联系管理员"
            }
        )
    except Exception as exc:
        logger.exception("未知错误")
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {exc}")


# ========== 教师端：题目识别与解答 API ==========

@app.post("/api/v1/solve", response_model=SolveQuestionResponse)
async def solve_questions(req: SolveQuestionRequest):
    """【教师端】识别指定题目并给出完整解答。

    教师上传包含多道题目的图片（如第一章总练习），
    并指定要解答的题目（如"第一大题第3小题，第三大题"），
    AI 识别对应题目并给出精确的完整解答。

    ## 指定格式示例
    - `第3题` / `3` → 第3题
    - `第一大题第3小题` / `一、3` → 第一大题第3小题
    - `第3大题` / `三、` → 第三大题全部
    - `1-3, 5, 7` → 第1-3题、第5题、第7题
    - `一、3；三、2` → 第一大题第3小题 + 第三大题第2小题
    """
    print(f"\n>>> 收到题目求解请求: {req.specifications}")

    if not settings.AI_VISION_API_KEY:
        raise HTTPException(status_code=503, detail="AI 服务未配置，请先设置 API Key")

    try:
        result = await call_solve_questions(
            image_base64=req.image_base64,
            specifications=req.specifications,
        )

        # 解析并构造响应
        questions = result.get("specified_questions", [])
        summary_data = result.get("summary", {})

        solved_questions = [
            SolvedQuestion(
                specification=q.get("specification", ""),
                found=q.get("found", False),
                q_number=q.get("q_number", ""),
                content=q.get("content", ""),
                question_type=q.get("question_type", ""),
                knowledge_points=q.get("knowledge_points", []),
                difficulty=q.get("difficulty", ""),
                solution=SolutionStep(
                    idea=q.get("solution", {}).get("思路", ""),
                    steps=q.get("solution", {}).get("步骤", []),
                    answer=q.get("solution", {}).get("答案", ""),
                ),
                full_solution=q.get("full_solution", ""),
                error_message=q.get("error_message", ""),
            )
            for q in questions
        ]

        summary = SolveSummary(
            total_specified=summary_data.get("total_specified", len(questions)),
            found_count=summary_data.get("found_count", sum(1 for q in questions if q.get("found"))),
            not_found=summary_data.get("not_found", []),
        )

        return SolveQuestionResponse(
            specified_questions=solved_questions,
            summary=summary,
        )

    except AIServiceError as exc:
        logger.error("AI 题目解答失败: %s", exc)
        raise HTTPException(
            status_code=422,
            detail={
                "error": "AI 返回数据解析失败",
                "message": str(exc),
                "hint": "可能是 LaTeX 公式转义错误，请重试或联系管理员"
            }
        )
    except Exception as exc:
        logger.exception("未知错误")
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {exc}")


@app.post("/api/v1/solve/upload", response_model=SolveQuestionResponse)
async def solve_questions_by_upload(
    file: UploadFile = File(...),
    specifications: str = File(..., description="题目指定，如：第一大题第3小题")
):
    """【教师端】上传图片并指定题目求解（multipart/form-data 版本）。

    适合前端直接上传文件的场景。
    """
    print(f"\n>>> 收到上传求解请求: {file.filename}, 指定: {specifications}")

    if file.content_type not in ("image/jpeg", "image/png", "image/webp"):
        raise HTTPException(status_code=400, detail="仅支持 JPEG / PNG / WebP 格式的图片")

    if not settings.AI_VISION_API_KEY:
        raise HTTPException(status_code=503, detail="AI 服务未配置，请先设置 API Key")

    contents = await file.read()
    if len(contents) > MAX_IMAGE_SIZE_MB * 1024 * 1024:
        raise HTTPException(status_code=400, detail=f"图片大小不能超过 {MAX_IMAGE_SIZE_MB}MB")

    image_base64 = base64.b64encode(contents).decode("utf-8")

    try:
        result = await call_solve_questions(
            image_base64=image_base64,
            specifications=specifications,
            mime_type=file.content_type or "image/png",
        )

        questions = result.get("specified_questions", [])
        summary_data = result.get("summary", {})

        solved_questions = [
            SolvedQuestion(
                specification=q.get("specification", ""),
                found=q.get("found", False),
                q_number=q.get("q_number", ""),
                content=q.get("content", ""),
                question_type=q.get("question_type", ""),
                knowledge_points=q.get("knowledge_points", []),
                difficulty=q.get("difficulty", ""),
                solution=SolutionStep(
                    idea=q.get("solution", {}).get("思路", ""),
                    steps=q.get("solution", {}).get("步骤", []),
                    answer=q.get("solution", {}).get("答案", ""),
                ),
                full_solution=q.get("full_solution", ""),
                error_message=q.get("error_message", ""),
            )
            for q in questions
        ]

        summary = SolveSummary(
            total_specified=summary_data.get("total_specified", len(questions)),
            found_count=summary_data.get("found_count", sum(1 for q in questions if q.get("found"))),
            not_found=summary_data.get("not_found", []),
        )

        return SolveQuestionResponse(
            specified_questions=solved_questions,
            summary=summary,
        )

    except AIServiceError as exc:
        logger.error("AI 题目解答失败: %s", exc)
        raise HTTPException(
            status_code=422,
            detail={
                "error": "AI 返回数据解析失败",
                "message": str(exc),
                "hint": "可能是 LaTeX 公式转义错误，请重试或联系管理员"
            }
        )
    except Exception as exc:
        logger.exception("未知错误")
        raise HTTPException(status_code=500, detail=f"服务器内部错误: {exc}")
