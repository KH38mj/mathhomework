# 微信云托管部署指南

## 📅 今日部署进展（2026-03-16）

### ✅ 已完成

| 步骤 | 状态 | 说明 |
|------|------|------|
| 开通云托管环境 | ✅ | 环境名称：`math-api-0g3espk659bcb48f` |
| 后端服务部署 | ✅ | 版本 `math-api-003`，状态：服务正常 |
| GitHub 自动部署配置 | ✅ | 已绑定仓库，代码 push 自动触发部署 |
| 前端 API 地址切换 | ✅ | 已切换到云托管生产环境 |
| 构建问题修复 | ✅ | 移除清华 PyPI 镜像，改用官方源 |

### 📋 当前配置

**云托管服务域名**：
```
https://math-api-234234-9-1324601200.sh.run.tcloudbase.com
```

**前端代码已更新**：`frontend/app.js` 中的 `apiBaseUrl` 已指向生产环境

### ⏳ 待完成（可选）

| 事项 | 状态 | 说明 |
|------|------|------|
| 配置 API Key 环境变量 | ✅ | 已填写 |
| 购买自定义域名 | ⏳ | 只有正式发布时才需要，测试可跳过 |
| 小程序合法域名配置 | ⏳ | 等待域名购买后配置 |

### 💡 域名方案对比

| 方案 | 首年费用 | 续费 | 建议 |
|------|---------|------|------|
| `.site` | ¥10 | ¥91/年 | 最便宜，但续费贵 |
| `.top` | ¥14 | ¥30-40/年 | 续费相对便宜 |
| `.store` | ¥12 | ？ | 备选 |

**建议**：先买 `.site` 首年 ¥10 测试，或每年换新域名薅首年优惠。

### 🧪 云端服务测试方法

#### 方法一：浏览器/Postman 直接测试（推荐）

打开浏览器访问：
```
https://math-api-234234-9-1324601200.sh.run.tcloudbase.com/api/v1/admin/config
```

应返回当前配置（不含敏感信息）。

#### 方法二：微信开发者工具测试

1. 微信开发者工具 → 右上角「详情」→「本地设置」
2. **勾选「不校验合法域名」**
3. 编译运行，正常测试所有功能
4. 此时请求会发送到云托管后端

#### 方法三：云端调试（控制台）

1. 云托管控制台 → 「云端调试」标签
2. 选择 **「公网访问」** 标签
3. 修改请求路径，例如：
   - 方法：`GET`
   - 路径：`/api/v1/admin/config`
4. 点击「调试」按钮
5. 查看返回结果

**注意**：云端调试适合快速验证后端是否响应，但接口有限，完整的业务测试建议用方法一或二。

#### 方法四：curl 命令行测试

```bash
curl -X GET \
  https://math-api-234234-9-1324601200.sh.run.tcloudbase.com/api/v1/admin/config \
  -H "Content-Type: application/json"
```

### ❓ 常见问题

**Q: 需要购买服务器吗？**
A: **不需要！** 微信云托管就是无服务器方案，已包含计算资源，按量计费。

**Q: 云托管默认域名为什么不能直接用？**
A: 微信小程序限制，云托管的 `.sh.run.tcloudbase.com` 域名仅限测试，正式环境必须用备案过的自定义域名。

---

## 前置准备

- [x] 小程序备案已完成
- [ ] 开通微信云开发
- [ ] 配置云托管服务
- [ ] 部署后端服务
- [ ] 配置小程序合法域名

---

## 第一步：开通微信云开发

1. 登录[微信小程序后台](https://mp.weixin.qq.com/)
2. 点击左侧菜单 **「云开发」**
3. 点击 **「开通」** 按钮
4. 选择环境名称（如 `mathhomework-prod`），点击 **「创建」**

> 注意：每个小程序可创建多个环境，建议生产/测试分开

---

## 第二步：开通云托管

1. 进入云开发控制台
2. 点击顶部 **「云托管」** 标签
3. 点击 **「立即开通」**
4. 勾选协议，点击 **「开通云托管」**

---

## 第三步：创建服务并部署

### 方式一：通过控制台部署（推荐首次）

1. 在云托管控制台点击 **「创建服务」**
2. 服务名称填写：`math-api`
3. 点击 **「新建版本」**

#### 上传代码部署

1. 选择 **「本地代码」** → **「上传压缩包」**
2. 将 `backend/` 目录压缩为 zip（不含 `venv/` 和 `uploads/`）
3. 上传压缩包
4. 填写版本号（如 `v1.0.0`）
5. 流量比例设为 **100%**
6. 点击 **「开始部署」**

### 方式二：通过 CLI 部署（推荐后续）

```bash
# 安装 CloudBase CLI
npm install -g @cloudbase/cli

# 登录
cloudbase login

# 进入后端目录
cd backend

# 部署（替换 env-id 为你的云开发环境ID）
cloudbase fn deploy --env-id mathhomework-prod-xxx
```

---

## 第四步：配置环境变量

### 当前方案（快速上线）

云托管容器是**无状态**的，容器重启后文件会重置。因此需要在环境变量中配置基础 API 信息，确保服务能正常启动：

1. 进入云托管 → 服务列表 → 点击 `math-api`
2. 点击 **「版本配置」** → **「编辑」**
3. 在 **「环境变量」** 区域添加（JSON 格式）：

```json
{
  "AI_VISION_API_KEY": "你的通义千问API_KEY",
  "AI_VISION_API_BASE_URL": "https://dashscope.aliyuncs.com/compatible-mode/v1",
  "AI_VISION_MODEL_NAME": "qwen-vl-max"
}
```

| 变量名 | 必填 | 说明 |
|--------|------|------|
| `AI_VISION_API_KEY` | ✅ | 通义千问 API Key（用于图片识别和批改） |
| `AI_VISION_API_BASE_URL` | ✅ | `https://dashscope.aliyuncs.com/compatible-mode/v1` |
| `AI_VISION_MODEL_NAME` | ✅ | `qwen-vl-max` |
| `AI_TEXT_API_KEY` | 可选 | 纯文本模型 Key（默认与视觉模型相同） |
| `SOLVE_API_KEY` | 可选 | 题目求解专用 Key（如 Gemini/Claude） |

4. 点击 **「保存」** → **「重新部署」**

### 关于后台管理配置

项目已支持后台管理页面（`/pages/admin/index`）动态调整配置：
- ✅ 启动时会读取**环境变量**作为默认配置
- ✅ 后台管理可临时覆盖配置（保存在 `.env` 文件）
- ⚠️ 但容器重启后，`.env` 文件会丢失，恢复为环境变量值

**建议**：基础配置填在环境变量，临时调试通过后台管理。

### 后期优化方向（配置持久化）

如需后台调整的配置永久保存，需要：
1. 开通**云开发数据库**（MongoDB）
2. 将配置存储在数据库中而非本地文件
3. 启动时从数据库读取配置覆盖环境变量

参考实现：`app/config.py` 添加数据库读取逻辑，工作量大但可行。

> **当前阶段**：先用环境变量方案，快速上线验证。用户量大或配置频繁变更时，再考虑数据库持久化改造。

---

## 第五步：配置小程序

### 1. 获取云托管域名

1. 云托管控制台 → 服务详情
2. 复制 **「公网访问域名」**（如 `https://math-api-xxx.service.cloudbase.cn`）

### 2. 配置合法域名

1. 小程序后台 → **「开发」** → **「开发管理」** → **「开发设置」**
2. 在 **「服务器域名」** 区域添加：

| 类型 | 域名 |
|------|------|
| request合法域名 | `https://math-api-xxx.service.cloudbase.cn` |
| uploadFile合法域名 | `https://cos.ap-xxx.myqcloud.com` |
| downloadFile合法域名 | `https://cos.ap-xxx.myqcloud.com` |

3. 保存并 **「提交审核」**（如提示需审核）

### 3. 修改小程序代码

编辑 `frontend/app.js`：

```javascript
globalData: {
  // 生产环境：云托管域名
  apiBaseUrl: 'https://math-api-xxx.service.cloudbase.cn',

  // 启用云存储
  useCloudStorage: true,

  studentProfile: null,
}
```

> 域名替换为你实际的云托管域名

### 4. 初始化云开发

编辑 `frontend/app.js` 的 `onLaunch`：

```javascript
onLaunch() {
  // 初始化云开发
  if (!wx.cloud) {
    console.error('请使用 2.2.3 或以上的基础库以使用云能力')
  } else {
    wx.cloud.init({
      env: 'mathhomework-prod-xxx', // 替换为你的环境ID
      traceUser: true,
    })
  }

  // 原有代码...
}
```

---

## 第六步：上传并发布小程序

1. 微信开发者工具 → 点击 **「上传」**
2. 填写版本号（如 `1.0.0`）和项目备注
3. 点击 **「上传」**
4. 进入小程序后台 → **「版本管理」**
5. 找到上传的版本 → 点击 **「提交审核」**
6. 审核通过后 → 点击 **「发布」**

---

## 验证部署

### 1. 测试后端服务

```bash
# 替换为你的云托管域名
curl https://math-api-xxx.service.cloudbase.cn/api/v1/admin/config \
  -X GET \
  -H "Content-Type: application/json"
```

### 2. 测试图片上传

1. 打开小程序
2. 进入学生端 → 选择作业
3. 拍照上传作业图片
4. 检查是否能正常提交并获取批改结果

---

## 常见问题

### Q1: 部署后提示 "容器启动失败"

检查点：
- Dockerfile 中的端口是否与 container.config.json 一致
- 查看云托管日志（控制台 → 日志）
- 确认 `requirements.txt` 完整

### Q2: 小程序提示 "不在合法域名列表"

检查点：
- 云托管域名已添加到 request 合法域名
- 域名包含 `https://` 前缀
- 域名修改后需重新编译小程序

### Q3: AI 批改超时

云托管默认请求超时 60 秒，AI 批改可能需要更久：

方案：改为异步流程
1. 提交后立即返回 `submission_id`
2. 前端轮询查询批改状态
3. 已完成（见 `assignment/detail.js`）

### Q4: 图片上传失败

- 确认云存储已开通
- 检查 `app.json` 中 `"cloud": true`
- 确认 `app.js` 中 `wx.cloud.init()` 已调用

---

## 费用说明

| 资源 | 免费额度 | 预估费用 |
|------|---------|---------|
| 容器实例 | 1 亿 GB·秒/月 | 免费（低流量） |
| 云存储 | 5 GB/月 | 免费 |
| 数据库 | 读 500 万次/月 | 免费 |
| 出网流量 | 1 GB/月 | 超出约 ¥0.8/GB |

---

## 后续维护

### 更新后端版本

1. 修改代码后重新打包 `backend/` 目录
2. 云托管控制台 → 新建版本
3. 灰度发布（先 10% 流量测试）
4. 观察日志无异常后全量发布

### 监控告警

云托管控制台 → 监控：
- 查看 QPS、响应时间、错误率
- 设置告警阈值（如 CPU > 80%）

### 日志查看

云托管控制台 → 日志：
- 实时查看容器日志
- 支持关键字搜索
- 支持导出

---

## 附录

### 目录结构

```
myproject/
├── backend/
│   ├── Dockerfile              # 容器配置
│   ├── container.config.json   # 云托管配置
│   ├── requirements.txt        # Python 依赖
│   └── app/                    # FastAPI 代码
├── frontend/
│   ├── app.js                  # 全局配置（含环境切换）
│   ├── app.json                # 小程序配置
│   └── utils/
│       └── cloudStorage.js     # 云存储工具
└── DEPLOY.md                   # 本文件
```

### 相关文档

- [微信云托管文档](https://developers.weixin.qq.com/miniprogram/dev/wxcloudrun/src/quickstart/)
- [云开发文档](https://developers.weixin.qq.com/miniprogram/dev/wxcloud/basis/getting-started.html)
