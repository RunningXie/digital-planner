# Dear Diary - 英文日记本

一个温馨的英文日记Web应用，帮助您用英文记录生活，并通过AI逐句批改提升英文写作水平。

## 功能特性

- 🔐 **账号系统** - 安全的用户注册与登录
- ✍️ **日记撰写** - 简洁优雅的写作界面
- 🤖 **AI批改** - 逐句分析英文表达，提供优化建议
- 🔍 **短语搜索** - 写作时随时搜索地道英文表达
- 📚 **日记管理** - 查看历史日记和批改记录

## 技术栈

| 层 | 技术 |
|-----|------|
| 后端 | Python 3.11 + FastAPI |
| 前端 | Jinja2 模板 + 原生 JavaScript |
| 数据库 | SQLAlchemy + SQLite |
| AI | 兼容 OpenAI-compatible API (智谱清言 GLM-4) |
| 认证 | JWT |
| 部署 | Docker + Docker Compose |

## 项目结构

```
digital-planner/
├── ai_service.py          # AI 服务封装：日记批改、短语搜索
├── auth.py                # JWT 认证逻辑
├── config.py              # 配置管理（pydantic-settings）
├── database.py            # SQLAlchemy 初始化
├── main.py                # FastAPI 应用入口
├── models.py              # 数据库模型 (User, Diary)
├── schemas.py             # Pydantic 模型定义
├── requirements.txt       # Python 依赖
├── static/
│   ├── css/style.css      # 样式
│   └── js/app.js          # 前端 API 封装
├── templates/
│   ├── base.html          # 基础模板
│   ├── index.html         # 首页
│   ├── login/register.html # 登录注册
│   ├── write.html         # 写日记页面（批改展示在这里）
│   └── diaries.html       # 日记列表
├── tests/                 # 集成测试
│   ├── conftest.py        # pytest fixtures
│   ├── test_json_parsing.py # JSON 解析单元测试
│   ├── test_diary_api.py  # API 集成测试
│   └── test_phrase_search.py # 短语搜索集成测试
├── .env                   # 环境变量（API key 等）
├── Dockerfile             # Docker镜像
├── docker-compose.yml     # Docker编排
└── README.md              # 项目说明文档
```

## 快速开始

### 本地开发

1. 安装依赖:
```bash
pip install -r requirements.txt
pip install pytest pytest-asyncio httpx  # 测试依赖
```

2. 配置环境变量:
```bash
# 编辑 .env 文件，设置您的API密钥
```

`.env` 文件内容示例：
```env
# Database
DATABASE_URL=sqlite:///./diary.db

# AI (OpenAI-compatible)
AI_BASE_URL=https://open.bigmodel.cn/api/paas/v4
AI_API_KEY=your-api-key-here
AI_MODEL=glm-4.5-air

# Security
SECRET_KEY=your-secret-key-change-in-production
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

# App
APP_HOST=0.0.0.0
APP_PORT=8000
DEBUG=true
```

3. 运行应用:
```bash
python main.py
# or
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

应用将在 http://localhost:8000 启动

### Docker部署

```bash
docker-compose up -d
```

### 运行测试

```bash
# 运行所有测试
pytest tests/ -v

# 单独运行 JSON 解析测试
pytest tests/test_json_parsing.py -v

# 单独运行 API 测试
pytest tests/test_diary_api.py -v

# 单独运行短语搜索测试
pytest tests/test_phrase_search.py -v
```

## 核心组件设计

### 1. `AIService.correct_diary()` — AI 日记批改

**输入**: `content: str`（用户日记原文）

**输出**: `Dict`
```python
{
  "corrections": [
    {
      "original": "原文句子",
      "corrected": "修正后的句子",
      "explanation": "错误说明",
      "suggestions": ["替代表达1", "替代表达2"]
    }
  ],
  "optimized_content": "全文优化版本",
  "error": "错误信息（如果失败）"  # 可选
}
```

**提示词设计要点**：
- **强制逐句输出**：必须为每个句子返回条目
- **列举常见错误**：中国学生常犯的错误示例（缺冠词、缺介词、拼写错误等）
- **正确句子也需要条目**：`explanation = "No errors found."`
- **降低 temperature 到 0.1**：提高输出确定性

**JSON 解析策略**（`_parse_json_response()`）：

| 优先级 | 策略 | 场景 |
|--------|------|------|
| 1 | `json.loads()` 直接解析 | AI 返回纯 JSON |
| 2 | 正则提取 ` ```json` / ` ```` 代码块 | AI 返回 markdown 格式 |
| 3 | 提取 `json { ... }` | AI 返回 `json` 前缀不包 backticks |
| 4 | 最外层花括号匹配 | JSON 嵌入在其他文本中 |

### 2. `AIService.search_phrase()` — 短语搜索

**输入**:
- `phrase: str` — 要搜索的短语
- `source_lang: str = "zh"`
- `target_lang: str = "en"`

**流程**:
1. 先查内存缓存（TTL 1小时），命中直接返回（毫秒级）
2. 未命中调用 AI，并缓存结果

**输出格式**:
```python
{
  "phrase": "...",
  "translations": ["翻译1", "翻译2"],
  "examples": ["例句1", "例句2"],
  "alternatives": ["替代说法1", ...],
  "source": "ai"
}
```

### 3. 数据库模型

**`User`**:
- `id`, `username`, `email`, `hashed_password`

**`Diary`**:
- `id`, `user_id` (FK), `title`, `content`
- `diary_date` — 用户选择的日记日期
- `corrections: JSON` — 存储 AI 批改结果数组
- `optimized_content: Text` — 优化后的全文
- `ai_error: Text` — AI 错误信息

### 4. API 端点

所有 API 路径前缀 `/api`

| 方法 | 路径 | 认证 | 说明 |
|------|------|------|------|
| POST | `/api/auth/register` | 否 | 用户注册 |
| POST | `/api/auth/login` | 否 | 获取 JWT |
| GET  | `/api/auth/me` | 是 | 获取当前用户 |
| POST | `/api/diaries` | 是 | 创建日记 + 触发 AI 批改 |
| GET  | `/api/diaries` | 是 | 获取当前用户所有日记 |
| GET  | `/api/diaries/{id}` | 是 | 获取单个日记 |
| PUT  | `/api/diaries/{id}` | 是 | 更新日记，修改内容会重新触发 AI 批改 |
| DELETE | `/api/diaries/{id}` | 是 | 删除日记 |
| POST | `/api/search-phrase/stream` | 是 | 搜索短语（流式响应） |

## 前端流程

### `write.html` 保存 + 批改流程

```
用户点击「保存并批改」
  ↓
saveDiary()
  → 检查重复点击 (_isSaving 锁 + disable button)
  → 显示 loading overlay
  → POST /api/diaries
  → 接收响应
  → displayCorrections()
  → 隐藏 loading overlay
  → 解锁按钮
```

**重复点击防护**：
- 模块级变量 `_isSaving`
- 点击后立即返回，如果正在保存
- finally 块保证解锁

**批改结果显示逻辑**:
1. 如果 `diary.error` → 显示红色错误卡片
2. 如果 `corrections` 非空 → 分离 `hasErrors` / `noErrors`
   - 有错误的句子显示单独卡片
   - 无错误的句子底部显示统计 `✅ N 个句子没有错误`
3. 如果 `corrections` 为空 → 提示 `⚠️ AI 未返回批改结果，请重试`
4. `optimized_content` 非空才显示优化区域

## 集成测试体系

### 测试覆盖范围

| 模块 | 测试覆盖 | 用例数 |
|------|----------|--------|
| `_parse_json_response()` | 所有解析策略 + 错误场景 + 真实 AI 格式 | 20 |
| POST /api/diaries | 成功、空内容、AI 错误、空结果 | 16 |
| POST /api/search-phrase/stream | 流式响应、错误处理、语言参数 | 8 |
| **总计** | | **44 个通过 + 2 个跳过** |

## 腾讯云部署指南

1. 在腾讯云服务器上安装Docker和Docker Compose

2. 复制项目文件到服务器:
```bash
scp -r digital-planner/ root@your-server-ip:/opt/
```

3. 在服务器上启动:
```bash
cd /opt/digital-planner
docker-compose up -d
```

4. 配置Nginx反向代理（可选）:
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

## 使用说明

1. 访问首页，注册账号
2. 登录后进入写日记页面
3. 用英文撰写日记，点击"保存并批改"
4. 查看AI批改结果和优化版本
5. 在写作过程中可以使用短语搜索功能查找表达

## 注意事项

- 请妥善保管您的AI API密钥
- 生产环境请修改SECRET_KEY
- 建议在生产环境使用PostgreSQL替代SQLite
- 定期备份数据库文件

## 持续改进

| 优先级 | 改进方向 |
|--------|----------|
| P1 | 缓存 AI 批改结果，避免重复请求 |
| P2 | 支持导出批改报告 PDF |
| P3 | 用户自定义 AI 提示词模板 |

## License

MIT License
