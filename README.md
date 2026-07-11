# Dear Diary - 英文日记本

一个温馨的英文日记Web应用，帮助您用英文记录生活，并通过AI逐句批改提升英文写作水平。

## 功能特性

- 🔐 **账号系统** - 安全的用户注册与登录
- ✍️ **日记撰写** - 简洁优雅的写作界面
- 🤖 **AI批改** - 逐句分析英文表达，提供优化建议
- 🔍 **短语搜索** - 写作时随时搜索地道英文表达
- 📚 **日记管理** - 查看、编辑、删除历史日记和批改记录
- ✏️ **日记编辑** - 修改过往日记的标题、日期和内容，AI 批改会自动重新生成

## 技术栈

| 层 | 技术 |
|-----|------|
| 后端 | Python 3.11 + FastAPI |
| 前端 | Jinja2 模板 + 原生 JavaScript |
| 数据库 | SQLAlchemy（开发用 SQLite，生产用 PostgreSQL） |
| AI | 兼容 OpenAI-compatible API（智谱清言 GLM-4） |
| 认证 | JWT |
| 部署 | Docker |

## 项目结构

```
digital-planner/
├── ai_service.py          # AI 服务封装：日记批改、短语搜索
├── auth.py                # JWT 认证逻辑
├── config.py              # 配置管理（pydantic-settings）
├── database.py            # SQLAlchemy 初始化
├── main.py                # FastAPI 应用入口
├── models.py              # 数据库模型 (User, Diary, Notebook, Quota)
├── schemas.py             # Pydantic 模型定义
├── requirements.txt       # Python 依赖
├── static/
│   ├── css/style.css      # 统一设计系统（温暖极简）
│   └── js/app.js          # 前端 API 封装
├── templates/
│   ├── base.html          # 基础模板（含顶部导航）
│   ├── index.html         # 首页
│   ├── login.html         # 登录
│   ├── register.html      # 注册（带邮箱验证码）
│   ├── forgot_password.html # 忘记密码（分步表单）
│   ├── write.html         # 写日记（批改展示在这里）
│   ├── diaries.html       # 日记列表
│   ├── notebook.html      # 笔记本
│   ├── admin.html         # 后台管理
│   └── admin_login.html   # 管理员登录
├── tests/                 # 集成测试
│   ├── conftest.py        # pytest fixtures
│   ├── test_json_parsing.py # JSON 解析单元测试
│   ├── test_diary_api.py  # API 集成测试
│   └── test_phrase_search.py # 短语搜索集成测试
├── start.sh               # 启停脚本
├── run_tests.sh           # 测试运行器
├── .env                   # 环境变量（API key 等）
├── Dockerfile             # Docker 镜像
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
# 构建镜像
docker build -t dear-diary .

# 运行容器
docker run -d -p 8000:8000 --env-file .env dear-diary
```

### 运行测试

```bash
# 运行所有测试（默认并发）
bash run_tests.sh

# 串行运行（debug 模式）
bash run_tests.sh --no-concurrency

# 或直接用 pytest
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

> **单一真相源** — 全部表结构都集中在 `models.py` 一个文件里。其他文件（`database.py` / `main.py` / `schemas.py` / 模板）都不再定义字段，只**消费** `models.py` 提供的字段。改字段只动一个地方。
>
> `database.py` 的 `init_db()` 启动时会：① `create_all` 建缺失的表；② 对比 `models.py` 和现有 DB schema，自动 `ALTER TABLE ADD COLUMN` 补齐新列；③ 回填带默认值的 NULL 行。**注意**：删列 / 改类型不会自动迁移，要手写 SQL。

#### 表结构（5 张表）

**`users` — 用户表**

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | Integer PK | 主键 |
| `username` | String(50) unique | 用户名（登录用） |
| `email` | String(100) unique | 邮箱 |
| `hashed_password` | String(255) | **bcrypt 哈希**（`bcrypt.gensalt()`） |
| `created_at` | DateTime | 注册时间 |
| `daily_token_used` | Integer default 0 | 今日已用 token |
| `daily_token_date` | Date | 配额重置日期 |
| `daily_token_limit` | Integer default 20000 | 每日 token 上限 |
| `last_active` | DateTime | 最近活跃时间（admin 统计用） |

**`diaries` — 日记表**

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | Integer PK | 主键 |
| `user_id` | Integer FK | 关联 `users.id` |
| `title` | String(200) default "" | 标题（已停用，默认空字符串） |
| `content` | Text | 日记正文 |
| `diary_date` | DateTime | 用户选择的日记日期 |
| `created_at` / `updated_at` | DateTime | 时间戳 |
| `corrections` | JSON | 逐句批改结果 |
| `optimized_content` | Text | AI 润色后整文 |
| `ai_error` | Text | AI 批改失败时的错误信息 |
| `weather` | String(16) | 写日记时的天气 |
| `mood` | String(16) | 写日记时的心情 |

**`notebook_entries` — 笔记本（用户收藏的短语）**

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | Integer PK | 主键 |
| `user_id` | Integer FK | 关联 `users.id` |
| `phrase` | String(200) indexed | 搜索过的短语 |
| `translations` | JSON | 翻译列表 |
| `examples` | JSON | 例句列表 |
| `alternatives` | JSON | 替代说法列表 |
| `note` | Text | 用户私人笔记 |
| `created_at` | DateTime | 加入时间 |
| `last_reviewed_at` | DateTime | 最近复习时间 |
| `review_count` | Integer default 0 | 复习次数 |

**`email_verification_codes` — 邮箱验证码**

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | Integer PK | 主键 |
| `email` | String(100) indexed | 接收验证码的邮箱 |
| `code` | String(10) | 6 位数字（短时明文，10 分钟过期、单次使用） |
| `created_at` / `expires_at` | DateTime | 时间戳 |
| `used` | Boolean default false | 是否已使用 |

**`dictionary_entries` — 雅思词条（离线词库）**

| 字段 | 类型 | 说明 |
|---|---|---|
| `id` | Integer PK | 主键 |
| `word` | String(200) indexed | 单词原形（小写） |
| `word_normalized` | String(200) unique | 去空格/标点，用于精确匹配 |
| `translation` | JSON | 主要中文翻译列表 |
| `pos` | JSON | 词性列表 `['n.', 'v.']` |
| `phonetics` | String(200) | 音标 `/ɒˈrɪŋ.ɡəl/` |
| `collins` | Integer default 0 | 柯林斯星级 1–5 |
| `frq` | Integer | 词频排序（数字越小越常用） |
| `tags` | JSON | 标签 `['ielts', 'cet4', 'toefl']` |
| `source` | String(50) default "ielts-ecdict" | 数据来源 |
| `created_at` | DateTime | 入库时间 |

**表关系**：`users 1───n diaries`，`users 1───n notebook_entries`。`email_verification_codes` 和 `dictionary_entries` 独立。

#### 字段加密现状

| 字段 | 表 | 方式 | 风险 |
|---|---|---|---|
| `hashed_password` | `users` | **bcrypt**（单向哈希） | ✅ 强 |
| JWT 登录态 | — | `python-jose` HS256 签名 | ⚠️ 签名非加密，载荷 base64 可解 |
| `email` / `username` | `users` | 明文 | ⚠️ PII |
| `content` / `note` | `diaries` / `notebook_entries` | **明文** | ⚠️ 私密日记内容 |
| `corrections` / `optimized_content` | `diaries` | 明文 | ⚠️ 含批改内容 |
| `code` | `email_verification_codes` | 明文 | ✅ 10 分钟过期、单次 |
| `dictionary_entries.*` | `dictionary_entries` | 明文 | ✅ 公开数据 |

HTTPS 传输由 Dokploy / 反向代理负责。**最敏感的是 `diaries.content` 和 `notebook_entries.note`** — 拿到 DB 备份或 SQL 注入就能直接读到所有用户私密内容。如要加固，方案是 `cryptography.fernet` 字段加密（密钥放环境变量 `DIARY_ENCRYPTION_KEY`）。

#### 雅思词条 PG 化（离线词库）

短语搜索的三级缓存：

```
用户笔记本 (notebook_entries)
    ↓ miss
PG dictionary_entries (~19k 雅思词条, 内存索引 O(1))
    ↓ miss
AI service.search_phrase_stream
```

**数据源**：开源 [ECDict](https://github.com/skywind3000/ECDICT) 英汉词典（BSD 协议），用 `scripts/load_ielts_dictionary.py` 灌入。

**筛选规则**（任一满足即可）：
- 标签属于 `{ielts, toefl, cet4, cet6, gre}`
- 或 `collins >= 1`（柯林斯星级）

**部署时灌入**：
```bash
# 1) 启动时 init_db 会自动 create_all 建表
# 2) 上传 ECDict CSV（65MB）到容器 /app/data/ecdict.csv
# 3) 灌入
docker exec <container> python scripts/load_ielts_dictionary.py \
    --csv-path /app/data/ecdict.csv --no-download --truncate
```

**源码位置**：
- 模型：[models.py](file:///home/xieyichen/digital-planner/models.py) `DictionaryEntry`
- 内存索引 + 搜索：[static_dictionary.py](file:///home/xieyichen/digital-planner/static_dictionary.py)
- 灌入脚本：[scripts/load_ielts_dictionary.py](file:///home/xieyichen/digital-planner/scripts/load_ielts_dictionary.py)
- API 集成：[main.py](file:///home/xieyichen/digital-planner/main.py) `/api/search-phrase/stream`（命中返回 `source: "ielts"`，短路 AI 调用、不消耗 token 配额）

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
| POST | `/api/diaries/stream` | 是 | 流式批改（无日记时新建） |
| PUT  | `/api/diaries/{id}/stream` | 是 | 流式批改（**复用日记**，避免重复记录） |
| POST | `/api/diaries/draft` | 是 | 保存日记（仅落库，不跑批改；"保存"按钮和自动保存都用它） |
| PUT  | `/api/diaries/{id}/draft` | 是 | 更新已存在的日记（自动保存复用） |
| POST | `/api/search-phrase/stream` | 是 | 搜索短语（流式响应） |

### 保存与批改的复用关系（避免重复记录）

写日记页面有 **两个保存路径**：
- **保存按钮** / **自动保存**（节流 2s）：`POST/PUT /api/diaries/draft`，不跑批改、只存原文
- **批改按钮**：`POST/PUT /api/diaries/stream`，跑 AI 批改并落库

**问题**：用户先写一段、触发了自动保存（日记 A），再修改文字、点批改 — 如果批改走 `POST /stream` 会**新建 B**，结果列表页看到 A 和 B 两条。

**修复**：批改按钮检测到 `_currentDiaryId` 时改走 `PUT /diaries/{id}/stream`（更新日记后再批改），DB 里只产生 1 条。`_currentDiaryId` 在 SSE `done` 事件里同步。

```
写日记
 ├─ 自动保存（每 2s 节流）
 │   ├─ 没日记 → POST /diaries/draft       → 存 _currentDiaryId=A
 │   └─ 有日记 → PUT  /diaries/A/draft     → 更新
 │
 └─ 点「批改」
     ├─ 没日记 → POST /diaries/stream       → 新建 B
     └─ 有日记 → PUT  /diaries/A/stream     → 复用 A（关键：避免重复）
```

**配额**：批改按新内容估算 token 扣费；保存不消耗配额。

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

### 使用 Dokploy 部署（推荐）

1. 在腾讯云服务器上安装 Docker 和 Dokploy

2. 在 Dokploy 控制台中添加应用，选择 Dockerfile 部署方式

3. 配置环境变量：
   ```
   DATABASE_URL=postgresql://user:password@host:5432/dbname
   AI_API_KEY=your-api-key
   AI_BASE_URL=https://open.bigmodel.cn/api/paas/v4
   AI_MODEL=glm-4.5-air
   SECRET_KEY=your-secret-key
   ```

4. 部署应用

### 手动 Docker 部署

1. 在腾讯云服务器上安装 Docker

2. 复制项目文件到服务器:
```bash
scp -r digital-planner/ root@your-server-ip:/opt/
```

3. 在服务器上构建并运行:
```bash
cd /opt/digital-planner
docker build -t dear-diary .
docker run -d -p 8000:8000 --env-file .env dear-diary
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
| P1 | Token 配额支持管理员后台手动调整 |
| P2 | 支持导出批改报告 PDF |
| P3 | 用户自定义 AI 提示词模板 |

## License

MIT License
