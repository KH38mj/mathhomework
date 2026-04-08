"""SQLite-backed persistence for assignments, submissions, and sessions."""

from __future__ import annotations

import json
import secrets
import sqlite3
import threading
import uuid
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

from app.config import settings
from app.models.schemas import AssignmentStatus
from app.schemas import AnswerMode, CorrectedQuestion, QuestionItem, StandardAnswer


@dataclass
class Assignment:
    id: str
    title: str
    questions: list[QuestionItem]
    answer_mode: AnswerMode | None = None
    standard_answers: list[StandardAnswer] = field(default_factory=list)
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    submit_start_time: str | None = None
    submit_end_time: str | None = None
    appeal_end_time: str | None = None
    allow_resubmit: bool = True
    allow_late: bool = True
    late_score_rule: str = "100%"
    course_id: str | None = None
    publish_status: str = "draft"


@dataclass
class Submission:
    id: str
    assignment_id: str
    student_id: str
    student_name: str
    image_url: str = ""
    status: AssignmentStatus = AssignmentStatus.pending
    corrected_questions: list[CorrectedQuestion] = field(default_factory=list)
    total_score: float = 0.0
    max_total_score: float = 0.0
    error_message: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    submit_status: str = "submitted"
    submit_time: str = field(default_factory=lambda: datetime.now().isoformat())
    is_late: bool = False
    resubmit_count: int = 0


@dataclass
class StudentSession:
    student_id: str
    display_name: str
    session_token: str
    created_at: str
    updated_at: str


_DB_PATH = settings.database_path
_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
_LOCK = threading.RLock()


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(_DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def _init_db() -> None:
    with _connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS assignments (
                id TEXT PRIMARY KEY,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS submissions (
                id TEXT PRIMARY KEY,
                assignment_id TEXT NOT NULL,
                student_id TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_submissions_assignment ON submissions(assignment_id)"
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_submissions_assignment_student
            ON submissions(assignment_id, student_id, created_at)
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS student_sessions (
                student_id TEXT PRIMARY KEY,
                display_name TEXT NOT NULL,
                session_token TEXT NOT NULL UNIQUE,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS admin_sessions (
                session_token TEXT PRIMARY KEY,
                created_at TEXT NOT NULL
            )
            """
        )


def _serialize_value(value: Any) -> Any:
    if isinstance(value, dict):
        return {key: _serialize_value(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_serialize_value(item) for item in value]
    if hasattr(value, "model_dump"):
        return _serialize_value(value.model_dump())
    if hasattr(value, "value"):
        return value.value
    return value


def _serialize_assignment(assignment: Assignment) -> dict[str, Any]:
    return {
        "id": assignment.id,
        "title": assignment.title,
        "questions": [_serialize_value(item) for item in assignment.questions],
        "answer_mode": assignment.answer_mode.value if assignment.answer_mode else None,
        "standard_answers": [_serialize_value(item) for item in assignment.standard_answers],
        "created_at": assignment.created_at,
        "submit_start_time": assignment.submit_start_time,
        "submit_end_time": assignment.submit_end_time,
        "appeal_end_time": assignment.appeal_end_time,
        "allow_resubmit": assignment.allow_resubmit,
        "allow_late": assignment.allow_late,
        "late_score_rule": assignment.late_score_rule,
        "course_id": assignment.course_id,
        "publish_status": assignment.publish_status,
    }


def _serialize_submission(submission: Submission) -> dict[str, Any]:
    return {
        "id": submission.id,
        "assignment_id": submission.assignment_id,
        "student_id": submission.student_id,
        "student_name": submission.student_name,
        "image_url": submission.image_url,
        "status": submission.status.value,
        "corrected_questions": [_serialize_value(item) for item in submission.corrected_questions],
        "total_score": submission.total_score,
        "max_total_score": submission.max_total_score,
        "error_message": submission.error_message,
        "created_at": submission.created_at,
        "submit_status": submission.submit_status,
        "submit_time": submission.submit_time,
        "is_late": submission.is_late,
        "resubmit_count": submission.resubmit_count,
    }


def _deserialize_assignment(payload: dict[str, Any]) -> Assignment:
    answer_mode = payload.get("answer_mode")
    return Assignment(
        id=payload["id"],
        title=payload["title"],
        questions=[QuestionItem(**item) for item in payload.get("questions", [])],
        answer_mode=AnswerMode(answer_mode) if answer_mode else None,
        standard_answers=[StandardAnswer(**item) for item in payload.get("standard_answers", [])],
        created_at=payload.get("created_at", datetime.now().isoformat()),
        submit_start_time=payload.get("submit_start_time"),
        submit_end_time=payload.get("submit_end_time"),
        appeal_end_time=payload.get("appeal_end_time"),
        allow_resubmit=payload.get("allow_resubmit", True),
        allow_late=payload.get("allow_late", True),
        late_score_rule=payload.get("late_score_rule", "100%"),
        course_id=payload.get("course_id"),
        publish_status=payload.get("publish_status", "draft"),
    )


def _deserialize_submission(payload: dict[str, Any]) -> Submission:
    return Submission(
        id=payload["id"],
        assignment_id=payload["assignment_id"],
        student_id=payload["student_id"],
        student_name=payload["student_name"],
        image_url=payload.get("image_url", ""),
        status=AssignmentStatus(payload.get("status", AssignmentStatus.pending.value)),
        corrected_questions=[CorrectedQuestion(**item) for item in payload.get("corrected_questions", [])],
        total_score=payload.get("total_score", 0.0),
        max_total_score=payload.get("max_total_score", 0.0),
        error_message=payload.get("error_message"),
        created_at=payload.get("created_at", datetime.now().isoformat()),
        submit_status=payload.get("submit_status", "submitted"),
        submit_time=payload.get("submit_time", datetime.now().isoformat()),
        is_late=payload.get("is_late", False),
        resubmit_count=payload.get("resubmit_count", 0),
    )


def save_assignment(assignment: Assignment) -> None:
    payload = json.dumps(_serialize_assignment(assignment), ensure_ascii=False)
    now = datetime.now().isoformat()
    with _LOCK, _connect() as conn:
        conn.execute(
            """
            INSERT INTO assignments(id, payload, created_at, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                payload=excluded.payload,
                updated_at=excluded.updated_at
            """,
            (assignment.id, payload, assignment.created_at, now),
        )


def get_assignment(assignment_id: str) -> Assignment | None:
    with _LOCK, _connect() as conn:
        row = conn.execute(
            "SELECT payload FROM assignments WHERE id = ?",
            (assignment_id,),
        ).fetchone()
    if not row:
        return None
    return _deserialize_assignment(json.loads(row["payload"]))


def list_assignments() -> list[Assignment]:
    with _LOCK, _connect() as conn:
        rows = conn.execute(
            "SELECT payload FROM assignments ORDER BY created_at DESC"
        ).fetchall()
    return [_deserialize_assignment(json.loads(row["payload"])) for row in rows]


def save_submission(submission: Submission) -> None:
    payload = json.dumps(_serialize_submission(submission), ensure_ascii=False)
    now = datetime.now().isoformat()
    with _LOCK, _connect() as conn:
        conn.execute(
            """
            INSERT INTO submissions(id, assignment_id, student_id, payload, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                payload=excluded.payload,
                assignment_id=excluded.assignment_id,
                student_id=excluded.student_id,
                updated_at=excluded.updated_at
            """,
            (
                submission.id,
                submission.assignment_id,
                submission.student_id,
                payload,
                submission.created_at,
                now,
            ),
        )


def get_submission(submission_id: str) -> Submission | None:
    with _LOCK, _connect() as conn:
        row = conn.execute(
            "SELECT payload FROM submissions WHERE id = ?",
            (submission_id,),
        ).fetchone()
    if not row:
        return None
    return _deserialize_submission(json.loads(row["payload"]))


def list_submissions_by_assignment(assignment_id: str) -> list[Submission]:
    with _LOCK, _connect() as conn:
        rows = conn.execute(
            """
            SELECT payload
            FROM submissions
            WHERE assignment_id = ?
            ORDER BY created_at DESC
            """,
            (assignment_id,),
        ).fetchall()
    return [_deserialize_submission(json.loads(row["payload"])) for row in rows]


def get_latest_submission_for_student(
    assignment_id: str,
    student_id: str,
) -> Submission | None:
    with _LOCK, _connect() as conn:
        row = conn.execute(
            """
            SELECT payload
            FROM submissions
            WHERE assignment_id = ? AND student_id = ?
            ORDER BY created_at DESC
            LIMIT 1
            """,
            (assignment_id, student_id),
        ).fetchone()
    if not row:
        return None
    return _deserialize_submission(json.loads(row["payload"]))


def mark_processing_submissions_failed(reason: str) -> int:
    updated = 0
    submissions = []
    with _LOCK:
        submissions = [
            submission
            for submission in list_submissions_by_assignment_all()
            if submission.status == AssignmentStatus.processing
        ]
        for submission in submissions:
            submission.status = AssignmentStatus.failed
            submission.error_message = reason
            save_submission(submission)
            updated += 1
    return updated


def list_submissions_by_assignment_all() -> list[Submission]:
    with _LOCK, _connect() as conn:
        rows = conn.execute(
            "SELECT payload FROM submissions ORDER BY created_at DESC"
        ).fetchall()
    return [_deserialize_submission(json.loads(row["payload"])) for row in rows]


def create_or_refresh_student_session(
    display_name: str,
    session_token: str | None = None,
) -> StudentSession:
    now = datetime.now().isoformat()
    with _LOCK, _connect() as conn:
        if session_token:
            row = conn.execute(
                """
                SELECT student_id, display_name, session_token, created_at, updated_at
                FROM student_sessions
                WHERE session_token = ?
                """,
                (session_token,),
            ).fetchone()
            if row:
                conn.execute(
                    """
                    UPDATE student_sessions
                    SET display_name = ?, updated_at = ?
                    WHERE session_token = ?
                    """,
                    (display_name, now, session_token),
                )
                return StudentSession(
                    student_id=row["student_id"],
                    display_name=display_name,
                    session_token=row["session_token"],
                    created_at=row["created_at"],
                    updated_at=now,
                )

        student_id = uuid.uuid4().hex
        new_token = secrets.token_urlsafe(32)
        conn.execute(
            """
            INSERT INTO student_sessions(student_id, display_name, session_token, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?)
            """,
            (student_id, display_name, new_token, now, now),
        )
        return StudentSession(
            student_id=student_id,
            display_name=display_name,
            session_token=new_token,
            created_at=now,
            updated_at=now,
        )


def get_student_session(session_token: str) -> StudentSession | None:
    with _LOCK, _connect() as conn:
        row = conn.execute(
            """
            SELECT student_id, display_name, session_token, created_at, updated_at
            FROM student_sessions
            WHERE session_token = ?
            """,
            (session_token,),
        ).fetchone()
    if not row:
        return None
    return StudentSession(
        student_id=row["student_id"],
        display_name=row["display_name"],
        session_token=row["session_token"],
        created_at=row["created_at"],
        updated_at=row["updated_at"],
    )


def create_admin_session() -> str:
    token = secrets.token_urlsafe(32)
    now = datetime.now().isoformat()
    with _LOCK, _connect() as conn:
        conn.execute(
            """
            INSERT INTO admin_sessions(session_token, created_at)
            VALUES (?, ?)
            """,
            (token, now),
        )
    return token


def is_admin_session_valid(session_token: str) -> bool:
    with _LOCK, _connect() as conn:
        row = conn.execute(
            "SELECT session_token FROM admin_sessions WHERE session_token = ?",
            (session_token,),
        ).fetchone()
    return row is not None


def revoke_admin_session(session_token: str) -> None:
    with _LOCK, _connect() as conn:
        conn.execute(
            "DELETE FROM admin_sessions WHERE session_token = ?",
            (session_token,),
        )


def database_path() -> Path:
    return _DB_PATH


_init_db()
