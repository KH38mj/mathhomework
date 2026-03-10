# AI 数学作业批改服务 - 项目进度

## 后端 (FastAPI) 状态

### 已完成

- [x] 基础目录结构
- [x] 配置管理 (.env 支持)
- [x] 图片接收接口 (上传/Base64)
- [x] AI Vision 服务封装 (兼容 OpenAI 格式)
- [x] Prompt 模板 (生成答案 + 批改)
- [x] 完整作业流程 API
  - 创建作业项目
  - AI/教师设置标准答案
  - 学生提交作业
  - 异步 AI 批改
- [x] 本地存储模拟 (预留 OSS 扩展)
- [x] 学生花名册管理 (手动添加/Excel导入)
- [x] JSON 解析容错处理（LaTeX 转义修复）
- [x] 本地开发端口统一改为 `18080`（后端/前端/测试脚本）
- [x] 新增一键启动脚本（`start_backend.ps1`，启动前自动清理端口占用）
- [x] 新增强制停止脚本（`stop_backend.ps1`，用于 Ctrl+C 失效场景）
- [x] **Git 仓库初始化并推送到 GitHub**（`https://github.com/wangweishi2018431/mathhomework`）

### 核心接口

| 接口 | 说明 |
|------|------|
| `POST /api/v1/correct/upload` | 【快速测试】上传图片直接批改，无需预创建作业 |
| `POST /api/v1/correct/base64` | 【快速测试】Base64 图片直接批改 |
| `POST /api/v1/assignments` | 创建作业项目 |
| `POST /api/v1/assignments/{id}/submit` | 学生提交作业（异步批改） |
| `GET /api/v1/assignments/{id}/submissions/{sid}` | 查询批改状态 |
| `POST /api/v1/courses` | 创建课程 |
| `POST /api/v1/courses/{id}/students/import` | 批量导入学生名单 |
| `POST /api/v1/admin/login` | 【管理端】管理员登录 |
| `GET /api/v1/admin/config` | 【管理端】获取当前配置 |
| `POST /api/v1/admin/config` | 【管理端】热更新配置 |
| `POST /api/v1/admin/config/test` | 【管理端】测试AI配置 |
| `POST /api/v1/admin/models` | 【管理端】获取模型列表（自动识别服务商） |
| `POST /api/v1/solve` | 【教师端】指定题目求解（Base64） |
| `POST /api/v1/solve/upload` | 【教师端】指定题目求解（文件上传） |
| `POST /api/v1/assignments/{id}/extend` | 【教师端】延长作业截止时间 |

### 配置 (.env)

```env
AI_API_KEY=your_api_key
AI_API_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
AI_MODEL_NAME=qwen-vl-max

# 教师端题目求解专用配置（可选，如 Gemini/Claude）
SOLVE_API_KEY=your_solve_api_key
SOLVE_API_BASE_URL=https://generativelanguage.googleapis.com/v1beta/openai
SOLVE_MODEL_NAME=gemini-2.5-pro-exp-03-25
```

---

## 前端 (微信小程序) 状态

### 已完成

- [x] 清理默认模板
- [x] 首页 UI 设计
  - 拍照/上传按钮
  - 图片预览区
  - 批改结果展示卡片
  - 状态提示区域
- [x] 核心交互逻辑
  - `wx.chooseMedia` 拍照/选图
  - `wx.uploadFile` 上传图片
  - 轮询查询批改状态
  - 结果渲染展示
- [x] 学生端登录（`wx.getUserProfile` 获取微信用户信息 + 本地登录态缓存）
- [x] **学生端首页 - 我的作业列表**
  - 登录后自动加载作业列表
  - 作业卡片：标题、状态标签、倒计时、班级进度
  - 状态排序：即将截止 > 进行中 > 待开始 > 已截止
  - 快速批改入口（弹窗形式，不干扰作业列表）
- [x] **学生端 - 作业详情与提交页面**
  - 作业信息展示：标题、时间、规则
  - 提交状态显示：未提交/批改中/已完成
  - 拍照上传作业图片
  - 实时轮询批改状态
  - 查看批改结果详情
- [x] 教师端页面（Tab 子界面）
  - **课程管理 Tab**：创建课程、选择课程、管理花名册
  - **创建作业 Tab**：子 Tab 切换
    - 作业列表：查看已创建作业、提交进度、截止时间状态、延长截止时间
    - 创建作业：两种模式二选一
      - 手动输入：直接输入题目和答案
      - 拍照上传：上传图片 → AI 识别题干和解答 → 编辑确认 → 创建作业
    - 时间配置：设置开始/截止/申诉时间
    - 规则配置：允许订正、允许逾期、逾期计分规则
- [x] 前端源码编码统一为 UTF-8 无 BOM（修复 `app.json` 解析错误）
- [x] **管理后台**
  - 配置热重载，在线修改 AI API 配置
  - **自动获取模型列表**：根据 Base URL 识别服务商，自动获取可用模型供下拉选择

### 文件结构

```
frontend/
├── app.js              # 全局配置（含 API 地址）
├── app.json            # 页面路由配置
├── app.wxss            # 全局样式
├── pages/
│   ├── index/          # 学生端首页
│   │   ├── index.js    # 作业列表 + 学生登录
│   │   ├── index.wxml  # 页面结构
│   │   ├── index.wxss  # 页面样式
│   │   └── index.json  # 页面配置
│   ├── assignment/     # 【新增】作业详情与提交
│   │   ├── detail.js   # 作业详情 + 提交
│   │   ├── detail.wxml
│   │   ├── detail.wxss
│   │   ├── detail.json
│   │   ├── result.js   # 批改结果展示
│   │   ├── result.wxml
│   │   ├── result.wxss
│   │   └── result.json
│   ├── teacher/        # 教师端页面
│   │   ├── index.js    # 课程/花名册/作业管理
│   │   ├── index.wxml
│   │   ├── index.wxss
│   │   └── index.json
│   └── admin/          # 管理后台
│       ├── index.js    # 配置热重载管理
│       ├── index.wxml
│       ├── index.wxss
│       └── index.json
└── project.config.json # 项目配置
```

---

## 本地开发启动步骤

### 1. 启动后端服务

```bash
cd D:/myproject/backend
# 确保 .env 已配置 AI_API_KEY
# 推荐：启动前自动清理残留进程（避免 Ctrl+C 未完全退出）
.\start_backend.ps1

# 或手动启动
uvicorn app.main:app --reload --port 18080
```

如遇 Ctrl+C 无法退出，可执行：`./stop_backend.ps1 -Port 18080`

### 2. 微信开发者工具设置（重要！）

打开微信开发者工具：

1. **导入项目**：选择 `D:/myproject/frontend` 目录
2. **设置不校验域名**：
   - 点击右上角「详情」按钮
   - 找到「本地设置」选项卡
   - **勾选「不校验合法域名、web-view（业务域名）、TLS 版本以及 HTTPS 证书」**

   ![设置位置](https://developers.weixin.qq.com/miniprogram/dev/image/devtools/nocheck.png)

3. 填入你的小程序 AppID（如果没有选测试号）

### 3. 测试流程

1. 确保后端已启动（`http://127.0.0.1:18080`）
2. 在微信开发者工具中点击「拍照/上传作业」按钮
3. 选择图片后自动上传
4. 等待 AI 批改完成
5. 查看批改结果卡片

---

## 已修复问题

### JSON 解析/LaTeX 转义问题（2026-03-06）

**问题**: AI 返回的 LaTeX 公式（如 `\int`）未正确转义，导致 JSON 解析失败

**修复措施**:
1. **强化 Prompt**: 所有 System Prompt 增加强制要求:
   - 务必直接输出纯 JSON，不要带 Markdown 代码块标记
   - LaTeX 反斜杠必须双重转义（`\\int` 而非 `\int`）

2. **JSON 清洗逻辑** (`ai_service.py`):
   - 自动移除 ` ```json ` 和 ` ``` ` 标记
   - 修复单层反斜杠为双重转义
   - 提取 `{...}` 之间的 JSON 内容

3. **错误处理**:
   - 返回 422 状态码而非 502
   - 详细错误信息包含行号、列号
   - 提示用户检查 LaTeX 转义


### Uvicorn Ctrl+C 未完全退出问题（2026-03-06）

**问题**: 本地开发时 `Ctrl+C` 偶发未完全关闭 `uvicorn`/监听进程，导致代码改动（如 `score` 逻辑）未生效或端口占用。

**修复措施**:
1. **端口迁移**: 本地联调端口从 `8000` 统一迁移为 `18080`，避免历史占用冲突。
2. **启动即清理**: 使用 `start_backend.ps1` 启动，先清理目标端口监听进程再拉起 `uvicorn --reload`。
3. **兜底停服**: 提供 `stop_backend.ps1 -Port 18080`，用于手动强制停止残留进程。
4. **联动同步**: 前端 API 地址、测试脚本与文档启动步骤全部同步到 `18080`。


### app.json JSON 解析报错（UTF-8 BOM）问题（2026-03-06）

**问题**: 微信开发者工具报错 `SyntaxError: Unexpected token in JSON at position 0`，定位到 `app.json` 首字节包含 UTF-8 BOM。

**修复措施**:
1. 将 `app.json`、`pages/teacher/index.json` 以及相关前端源码统一转换为 **UTF-8 无 BOM**。
2. 重新校验 `app.json` JSON 可解析性，确认配置结构有效。
3. 统一前端源码编码规范，避免后续同类解析错误复发。

---

## 测试数据（2026-03-07）

### 测试作业列表

| 作业 | ID | 截止时间 | 状态 | 题目数 | 满分 | 规则 | 提交进度 |
|------|-----|----------|------|--------|------|------|----------|
| 第一章 函数与极限 练习题 | 9f84b28c8916 | 3月10日 | 进行中 | 2题 | 25分 | 可订正、可逾期、逾期80% | 5/30 |
| 第二章 导数与微分 课后习题 | 988a314cc1ec | 2月28日 | 已截止 | 2题 | 20分 | 不可订正、不可逾期 | 8/30 |
| 第三章 积分初步 测试卷 | 4da3f95eae41 | 3月20日 | 待开始 | 4题 | 50分 | 可订正、可逾期、逾期60% | 0/30 |
| 期中复习 模拟测试 | fefdf03012ab | 3月8日 | **即将截止** | 3题 | 60分 | 可订正、可逾期、逾期100% | 0/30 |

### 查看效果

1. 启动后端: `cd D:/myproject/backend && ./start_backend.ps1`
2. 微信开发者工具导入 `D:/myproject/frontend`
3. 进入 **教师端** → **创建作业** Tab
4. 默认显示 **作业列表** 子 Tab

**界面元素：**
- **状态标签**：绿色(进行中)、红色(已截止)、橙色(即将截止/24小时内)、灰色(待开始/草稿)
- **进度条**：显示已提交人数比例
- **时间信息**：开始/截止/申诉时间
- **规则标签**：可订正、可逾期、逾期计分比例
- **操作按钮**：查看详情、延长截止时间

---

## 下一步计划

1. [x] 后端提交接口优化（支持快速提交无需预创建作业）
2. [x] 公式渲染组件集成 (mp-html 或 Towxml)
3. [x] 学生端登录功能（获取微信用户信息）
4. [x] 教师端页面（创建作业、管理花名册）
5. [x] 学生端作业列表页面
6. [ ] 微信云托管部署（等待小程序备案完成，预计一周）

---

## 学生端作业列表功能设计（2026-03-07）

参考微信图片中的界面设计，学生端需要实现作业列表页面，显示所属班级的作业及提交状态。

### 界面元素

```
┌─────────────────────────────────────────────┐
│ 高数A班          🔔      👤                 │  ← 顶部：班级选择 + 通知 + 个人中心
├─────────────────────────────────────────────┤
│                                             │
│ 10.3曲线长度曲率...              0/3       │  ← 作业卡片1
│ 提交: 2026-03-06 —— 2026-03-09            │
│ ! 申诉截止: 2026-03-12                    │
│ ●允许订正重交  ⏱逾期按100%计分  [查看作业] │
│                                             │
│ 10.2曲率...                      0/3       │  ← 作业卡片2
│ 提交: 2026-03-06 —— 2026-03-09            │
│ ○不可订正重交    ⏱逾期按0%计分   [去提交]  │
│                                             │
│ 9.8 曲线弧长...                  3/3       │  ← 作业卡片3（已完成）
│ 提交: 2026-03-06 —— 2026-03-09            │
│ ●允许订正重交    ⏱禁止延期       [查看作业]│
│                                             │
├─────────────────────────────────────────────┤
│ 📝 作业列表    📊 统计    👥 我的          │  ← 底部 Tab 导航
└─────────────────────────────────────────────┘
```

### 数据模型扩展

#### 作业表新增字段
```python
class Assignment(BaseModel):
    # 原有字段...
    class_id: str              # 关联班级ID
    submit_start_time: datetime   # 提交开始时间
    submit_end_time: datetime     # 提交截止时间
    appeal_end_time: datetime     # 申诉截止时间
    allow_resubmit: bool = True   # 是否允许订正重交
    late_score_rule: str = "100%" # 逾期计分规则：100%/80%/0%
    allow_late: bool = True       # 是否允许逾期提交
    status: str = "draft"         # 状态：draft/published/closed
```

#### 学生提交表新增
```python
class Submission(BaseModel):
    # 原有字段...
    submit_status: str         # not_submitted/submitted/graded/appealed
    submit_time: datetime      # 实际提交时间
    is_late: bool = False      # 是否逾期提交
    resubmit_count: int = 0    # 订正重交次数
```

### API 接口设计

| 接口 | 方法 | 功能 |
|------|------|------|
| `GET /api/v1/student/classes` | GET | 获取学生加入的班级列表 |
| `GET /api/v1/student/assignments` | GET | 获取作业列表（支持 class_id 筛选） |
| `GET /api/v1/student/assignments/{id}` | GET | 获取作业详情 |
| `GET /api/v1/student/assignments/{id}/progress` | GET | 获取作业提交进度（已交人数/总人数） |

#### 作业列表返回格式
```json
{
  "assignments": [
    {
      "id": "xxx",
      "title": "10.3曲线长度曲率...",
      "class_id": "xxx",
      "class_name": "高数A班",
      "progress": "0/3",
      "progress_percent": 0,
      "submit_start": "2026-03-06 10:59",
      "submit_end": "2026-03-09 12:00",
      "appeal_end": "2026-03-12 12:00",
      "allow_resubmit": true,
      "allow_late": true,
      "late_rule": "100%",
      "status": "ongoing",
      "my_submit_status": "not_submitted"
    }
  ]
}
```

### 状态判断逻辑

#### 作业时间状态
```javascript
const now = new Date();

if (now < submit_start) {
  status = "not_started";      // 未开始
} else if (now >= submit_start && now < submit_end) {
  status = "ongoing";          // 进行中（可提交）
} else if (now >= submit_end && now < appeal_end) {
  status = "appeal_period";    // 申诉期（不可新提交，可申诉）
} else {
  status = "closed";           // 已结束
}
```

#### 进度显示样式
| 进度 | 样式 |
|------|------|
| `0/3` | 黄色背景标签 |
| `1/3` `2/3` | 蓝色背景标签 |
| `3/3` | 绿色背景标签 |

#### 状态标签颜色
| 标签 | 颜色 |
|------|------|
| ●允许订正重交 | 蓝色 |
| ○不可订正重交 | 灰色 |
| ⏱逾期按100%计分 | 橙色 |
| ⏱逾期按0%计分 | 红色 |
| ⏱禁止延期 | 深红色 |

### 按钮状态
| 场景 | 按钮文字 | 跳转 |
|------|----------|------|
| 未提交 | 去提交 | 提交作业页 |
| 已提交/申诉期 | 查看作业 | 作业详情页 |
| 已截止 | 查看作业 | 作业详情页（只读） |

### 教师端配套更改

创建作业时需要设置以下新字段：

```javascript
// 创建作业请求
{
  "title": "10.3 曲线长度与曲率",
  "questions": [...],
  // 新增字段
  "submit_start_time": "2026-03-06T10:59:00",    // 提交开始时间
  "submit_end_time": "2026-03-09T12:00:00",      // 提交截止时间
  "appeal_end_time": "2026-03-12T12:00:00",      // 申诉截止时间（可选）
  "allow_resubmit": true,                         // 允许订正重交
  "allow_late": true,                             // 允许逾期提交
  "late_score_rule": "100%"                       // 逾期计分规则：100%/80%/60%/0%
}
```

教师端需要新增「作业管理」页面：
- 查看已发布作业列表
- 查看各作业提交进度（已交/未交/总人数）
- 查看作业状态（未开始/进行中/申诉期/已结束）
- 延长截止时间（紧急情况）

### 实现步骤

1. **数据模型扩展**：添加时间字段、规则字段到 Assignment 模型
2. **后端 API 开发**：
   - 修改创建作业接口，支持新字段
   - 实现教师作业列表/管理接口
   - 实现学生班级查询接口
   - 实现学生作业列表接口（含进度统计）
3. **前端页面开发**：
   - **教师端**：完善创建作业表单（时间选择器、开关、下拉选择）
   - **教师端**：新增作业管理页面
   - **学生端**：创建 `pages/student/index` 作业列表页面
   - 实现顶部导航（班级选择 + 通知 + 个人中心）
   - 实现作业卡片组件
   - 实现底部 Tab 导航
4. **状态逻辑实现**：时间判断、标签颜色、按钮状态
5. **联调测试**：验证各种时间场景下的显示逻辑










