"""课程学生名单服务 —— 老师手动导入/管理。

数据持久化到本地 JSON 文件（data/rosters.json），
后续迁移数据库时只需替换存储层即可。
"""

from __future__ import annotations

import json
from pathlib import Path
from pydantic import BaseModel, Field

# ---- 数据模型 ----

class StudentInfo(BaseModel):
    student_id: str = Field(..., description="学号")
    name: str = Field(..., description="姓名")
    class_name: str = Field("", description="班级")


class CourseRoster(BaseModel):
    course_id: str
    course_name: str
    students: list[StudentInfo] = Field(default_factory=list)


# ---- 存储路径 ----

_DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"
_ROSTER_FILE = _DATA_DIR / "rosters.json"


def _ensure_data_dir() -> None:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)


def _load_all() -> dict[str, dict]:
    """从 JSON 文件加载全部花名册数据。"""
    if not _ROSTER_FILE.exists():
        return {}
    text = _ROSTER_FILE.read_text(encoding="utf-8")
    return json.loads(text) if text.strip() else {}


def _save_all(data: dict[str, dict]) -> None:
    """将全部花名册数据写入 JSON 文件。"""
    _ensure_data_dir()
    _ROSTER_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


def get_course_student_count(course_id: str | None) -> int:
    if not course_id:
        return 0
    data = _load_all()
    course = data.get(course_id)
    if not course:
        return 0
    return len(course.get("students", []))


# ---- 服务类 ----

class RosterService:
    """花名册管理服务：增删查 + 批量导入。"""

    # ---------- 课程 ----------

    async def create_course(self, course_id: str, course_name: str) -> CourseRoster:
        """创建课程（若已存在则返回现有数据）。"""
        data = _load_all()
        if course_id not in data:
            data[course_id] = {
                "course_id": course_id,
                "course_name": course_name,
                "students": [],
            }
            _save_all(data)
        return CourseRoster(**data[course_id])

    async def list_courses(self) -> list[CourseRoster]:
        """列出所有课程及其花名册。"""
        data = _load_all()
        return [CourseRoster(**v) for v in data.values()]

    async def delete_course(self, course_id: str) -> bool:
        """删除课程。返回是否存在并被删除。"""
        data = _load_all()
        if course_id in data:
            del data[course_id]
            _save_all(data)
            return True
        return False

    # ---------- 学生 ----------

    async def get_students_by_course(self, course_id: str) -> CourseRoster:
        """获取某门课程的学生名单。"""
        data = _load_all()
        if course_id not in data:
            return CourseRoster(
                course_id=course_id,
                course_name=f"未知课程 ({course_id})",
                students=[],
            )
        return CourseRoster(**data[course_id])

    async def add_student(self, course_id: str, student: StudentInfo) -> CourseRoster:
        """向课程中添加单个学生（学号去重）。"""
        data = _load_all()
        if course_id not in data:
            raise ValueError(f"课程 {course_id} 不存在，请先创建课程")
        existing_ids = {s["student_id"] for s in data[course_id]["students"]}
        if student.student_id not in existing_ids:
            data[course_id]["students"].append(student.model_dump())
            _save_all(data)
        return CourseRoster(**data[course_id])

    async def remove_student(self, course_id: str, student_id: str) -> CourseRoster:
        """从课程中移除某个学生。"""
        data = _load_all()
        if course_id not in data:
            raise ValueError(f"课程 {course_id} 不存在")
        data[course_id]["students"] = [
            s for s in data[course_id]["students"] if s["student_id"] != student_id
        ]
        _save_all(data)
        return CourseRoster(**data[course_id])

    async def batch_import_students(
        self, course_id: str, students: list[StudentInfo]
    ) -> CourseRoster:
        """批量导入学生（学号去重，已有的跳过）。"""
        data = _load_all()
        if course_id not in data:
            raise ValueError(f"课程 {course_id} 不存在，请先创建课程")
        existing_ids = {s["student_id"] for s in data[course_id]["students"]}
        for stu in students:
            if stu.student_id not in existing_ids:
                data[course_id]["students"].append(stu.model_dump())
                existing_ids.add(stu.student_id)
        _save_all(data)
        return CourseRoster(**data[course_id])
