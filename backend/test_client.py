import asyncio
import os
import time

import httpx

# 确保 FastAPI 后端已在本地启动，默认端口 18080
BACKEND_PORT = os.getenv("BACKEND_PORT", "18080")
BASE_URL = os.getenv("BASE_URL", f"http://127.0.0.1:{BACKEND_PORT}/api/v1")

# 测试使用的数学图片，请确保当前目录下有这张图片
TEST_IMAGE_PATH = "test_math.jpg"

async def run_e2e_test():
    if not os.path.exists(TEST_IMAGE_PATH):
        print(f"❌ 未找到测试图片: {TEST_IMAGE_PATH}")
        print("请在 backend 目录下放一张真实的数学作业照片，命名为 test_math.jpg")
        return

    print("🚀 正在启动端到端测试链路...\n")

    async with httpx.AsyncClient(timeout=30.0) as client:
        # ==========================================
        # 步骤 1: 模拟老师创建作业项目
        # ==========================================
        print("👨‍🏫 [老师端] 1. 正在创建作业...")
        create_payload = {
            "title": "高等数学随堂测验 (本地测试)",
            "questions": [
                {
                    "type": "text",
                    "content": "请计算定积分: \\int_0^1 x^2 dx",
                    "max_score": 10.0
                }
            ]
        }
        resp = await client.post(f"{BASE_URL}/assignments", json=create_payload)
        resp.raise_for_status()
        assignment = resp.json()
        assignment_id = assignment["id"]
        print(f"✅ 作业创建成功! ID: {assignment_id}")

        # ==========================================
        # 步骤 2: 模拟老师提交标准答案
        # ==========================================
        print(f"👨‍🏫 [老师端] 2. 正在为作业 {assignment_id} 提交标准答案...")
        answer_payload = {
            "answers": [
                {
                    "question_index": 0,
                    "answer": "\\int_0^1 x^2 dx = [\\frac{x^3}{3}]_0^1 = \\frac{1}{3} - 0 = \\frac{1}{3}"
                }
            ]
        }
        resp = await client.post(f"{BASE_URL}/assignments/{assignment_id}/answers/teacher-submit", json=answer_payload)
        resp.raise_for_status()
        print("✅ 标准答案设置成功!\n")

        print("🧑‍🎓 [学生端] 2.5 正在创建学生会话...")
        session_resp = await client.post(
            f"{BASE_URL}/student/session",
            json={"display_name": "本地测试学生-张三"},
        )
        session_resp.raise_for_status()
        student_session = session_resp.json()
        student_token = student_session["session_token"]
        print("✅ 学生会话创建成功!\n")

        # ==========================================
        # 步骤 3: 模拟学生上传图片并触发异步批改
        # ==========================================
        print("🧑‍🎓 [学生端] 3. 正在上传图片并提交作业...")

        # 构造 multipart/form-data
        with open(TEST_IMAGE_PATH, "rb") as f:
            files = {
                "file": (TEST_IMAGE_PATH, f, "image/jpeg")
            }
            resp = await client.post(
                f"{BASE_URL}/assignments/{assignment_id}/submit",
                files=files,
                headers={"X-Student-Token": student_token},
            )

        if resp.status_code != 202:
            print(f"❌ 上传失败! 状态码: {resp.status_code}, {resp.text}")
            return

        submission = resp.json()
        submission_id = submission["submission_id"]
        status = submission["status"]
        print(f"✅ 提交成功! 获得任务 ID: {submission_id}, 初始状态: {status}\n")

        # ==========================================
        # 步骤 4: 轮询批改结果
        # ==========================================
        print("🔄 [前端] 4. 开始轮询批改状态...")

        max_attempts = 40  # 约 120 秒超时
        attempts = 0

        while attempts < max_attempts:
            attempts += 1
            print(f"   ⏳ 第 {attempts} 次查询状态...")

            resp = await client.get(
                f"{BASE_URL}/assignments/{assignment_id}/submissions/{submission_id}",
                headers={"X-Student-Token": student_token},
            )
            resp.raise_for_status()

            current_data = resp.json()
            current_status = current_data["status"]

            if current_status == "completed":
                print("\n🎉 批改完成!")
                print("="*50)
                print(f"总得分: {current_data['total_score']} / {current_data['max_total_score']}")

                for idx, q in enumerate(current_data["questions"]):
                    print(f"\n[第 {idx+1} 题]")
                    print(f"判定: {'✅ 正确' if q['is_correct'] else '❌ 错误/部分正确'} | 得分: {q['score']}/{q['max_score']}")
                    print(f"AI 识别内容: {q.get('content', '')}")
                    print(f"学生解答: {q.get('student_ans', '')}")
                    print(f"详细分析:\n{q.get('analysis', '')}")
                print("="*50)
                break

            elif current_status == "failed":
                print(f"\n❌ 批改失败!\n错误原因: {current_data.get('error_message', '未知错误')}")
                break

            else:
                # status == 'processing' 或 'pending'
                await asyncio.sleep(3)

        if attempts >= max_attempts:
            print("\n⚠️ 轮询超时 (超过 120 秒)，请检查服务端日志。")

if __name__ == "__main__":
    asyncio.run(run_e2e_test())

