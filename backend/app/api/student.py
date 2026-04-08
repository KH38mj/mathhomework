from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.storage import create_or_refresh_student_session


router = APIRouter(prefix="/api/v1/student", tags=["student"])


class StudentSessionRequest(BaseModel):
    display_name: str = Field(..., min_length=1, max_length=100)
    session_token: str | None = None


class StudentSessionResponse(BaseModel):
    student_id: str
    display_name: str
    session_token: str


@router.post("/session", response_model=StudentSessionResponse)
async def create_student_session(req: StudentSessionRequest):
    session = create_or_refresh_student_session(
        display_name=req.display_name,
        session_token=req.session_token,
    )
    return StudentSessionResponse(
        student_id=session.student_id,
        display_name=session.display_name,
        session_token=session.session_token,
    )
