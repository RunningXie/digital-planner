# 技术文档：Dear Diary - 英文写作练习日记本

## 项目概览

**Dear Diary** 是一个基于 FastAPI + AI 的英文写作练习平台，用户可以：

- 用英文写日记
- AI 自动逐句批改语法、拼写、用词错误
- 提供替代表达和完整优化版本
- 短语搜索功能：查询中文 → 自然英文表达

### 技术栈

| 层 | 技术 |
|-----|------|
| 后端 | Python 3.11 + FastAPI |
| 前端 | Jinja2 模板 + 原生 JavaScript |
| 数据库 | SQLAlchemy + SQLite |
| AI | 兼容 OpenAI-compatible API (智谱清言 GLM-4) |
| 认证 | JWT |

---

## 目录结构

```
digital-planner/
├── ai_service.py          # AI 服务封装：日记批改、短语搜索
├── auth.py                # JWT 认证逻辑
├── config.py              # 配置管理（pydantic-settings）
├── database.py            # SQLAlchemy 初始化
├── main.py                # FastAPI 应用入口
├── models.py              # 数据库模型 (User, Diary)
├── schemas.py             # Pydantic 模型定义
├── phrase_dictionary.py   # 本地短语词典（可选）
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
├── tests/                 # 集成测试（新增）
│   ├── conftest.py        # pytest fixtures
│   ├── test_json_parsing.py # JSON 解析单元测试
│   └── test_diary_api.py  # API 集成测试
├── .env                   # 环境变量（API key 等）
├── Dockerfile / docker-compose.yml # 容器化部署
└── README.md              # 部署说明
```

---

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

**提示词设计要点**（2026-06-06 修复后）：

1. **强制逐句输出**：`NEVER return an empty corrections array. If the diary has N sentences, you MUST return N entries.`
2. **列举常见错误**：中国学生常犯的错误示例（缺冠词、缺介词、拼写错误等）
3. **正确句子也需要条目**：`even correct sentences → explanation = "No errors found."`
4. **降低 temperature 到 0.1**：提高输出确定性
5. **System Prompt 强调严格批改**：`You ALWAYS find errors in student writing`

**JSON 解析策略**（`_parse_json_response()`）：

| 优先级 | 策略 | 场景 |
|--------|------|------|
| 1 | `json.loads()` 直接解析 | AI 返回纯 JSON |
| 2 | 正则提取 ` ```json` / ` ```` 代码块 | AI 返回 markdown 格式 |
| 3 | 提取 `json { ... }` | AI 返回 `json` 前缀不包 backticks |
| 4 | 最外层花括号匹配 | JSON 嵌入在其他文本中 |

---

### 2. `AIService.search_phrase()` — 短语搜索

**输入**:
- `phrase: str` — 要搜索的短语
- `source_lang: str = "zh"`
- `target_lang: str = "en"`

**流程**:
1. 先查 `phrase_dictionary.py` 本地词典，命中直接返回（秒级）
2. 未命中才调用 AI

**输出格式**:
```python
{
  "phrase": "...",
  "translations": ["翻译1", "翻译2"],
  "examples": ["例句1", "例句2"],
  "alternatives": ["替代说法1", ...],
  "source": "local" / "ai"
}
```

---

### 3. 数据库模型

**`User`**:
- `id`, `username`, `email`, `hashed_password`

**`Diary`**:
- `id`, `user_id` (FK), `title`, `content`
- `diary_date` — 用户选择的日记日期
- `corrections: JSON` — 存储 AI 批改结果数组
- `optimized_content: Text` — 优化后的全文

---

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
| POST | `/api/search-phrase` | 是 | 搜索短语 |

---

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

---

## 已知问题 & 修复记录

### 问题 1：AI 返回空 `corrections` 数组，前端显示"没有需要修改的地方"

**根因**:
- 原提示词没有强制 AI 对每个句子输出条目
- AI 倾向于认为整体可读性尚可就跳过所有错误

**修复**:
- 重写提示词，逐条列出检查要点
- 明确禁止空数组：`NEVER return an empty corrections array`
- 要求即使正确句子也要输出条目，`explanation = "No errors found."`

---

### 问题 2：AI 返回 `json {...}` 格式，无法解析

**根因**:
- 原解析只匹配 ` ```json\n...\n``` `
- 不匹配 `json { ... }` 这种无 backticks 格式

**修复**:
- 引入 `_parse_json_response()` 多策略解析
- 支持：纯 JSON、markdown 代码块、`json` 前缀、任意文本中最外层 JSON

---

### 问题 3："保存并批改" 按钮重复点击 → 多次请求

**根因**:
- 没有加锁，快点击两下会发起两次请求

**修复** (2026-06-06):
- 添加 `_isSaving` 布尔锁
- 请求进行中禁用按钮
- finally 块保证解锁

---

## 环境配置 `.env`

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

---

## 运行和测试

### 安装依赖

```bash
pip install -r requirements.txt
pip install pytest pytest-asyncio httpx  # 测试依赖
```

### 开发启动

```bash
python main.py
# or
uvicorn main:app --reload --host 0.0.0.0 --port 8000
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

---

## 集成测试体系

### 测试文件结构

```
tests/
├── conftest.py           # pytest fixtures（测试基础设施）
├── test_json_parsing.py  # JSON 解析单元测试
├── test_diary_api.py     # 日记 API 集成测试
└── test_phrase_search.py # 短语搜索集成测试
```

### 1. `conftest.py` — 测试基础设施

| Fixture | 功能 |
|---------|------|
| `setup_database()` | 全局：创建/销毁 SQLite 内存数据库表 |
| `db_session()` | 每个测试：独立事务，自动回滚 |
| `test_user()` | 创建测试用户（testuser/testpass123） |
| `auth_headers()` | 返回 JWT 认证头 |
| `client()` | FastAPI TestClient，自动注入认证 |
| `mock_ai_service()` | Mock AI 服务返回正常结果 |
| `mock_ai_service_error()` | Mock AI 返回错误（500） |
| `mock_ai_service_empty()` | Mock AI 返回空修正（模拟 bug） |
| `mock_ai_service_401()` | Mock AI 返回认证错误（API key 过期） |

### 2. `test_json_parsing.py` — JSON 解析单元测试

**测试目标**：验证 `_parse_json_response()` 多策略解析器能正确处理各种 AI 返回格式。

**覆盖的解析策略**：

| 策略 | 格式示例 | 测试用例数 |
|------|----------|-----------|
| 纯 JSON | `{"corrections":[...]}` | 3 |
| Markdown 代码块 | `\`\`\`json\n{...}\n\`\`\`` | 5 |
| `json` 前缀 | `json {...}` | 2 |
| 花括号匹配 | `text {...} more` | 3 |

**错误场景测试**：无效字符串、空字符串、格式错误、截断 JSON（共 4 个用例）

**真实场景测试**：GLM API 实际返回格式（3 个用例）+ Segovia 日记完整场景（1 个用例）

### 3. `test_diary_api.py` — 日记 API 集成测试

#### `TestCreateDiary` — 创建日记
- `test_create_diary_success`：正常创建 + AI 批改
- `test_create_diary_without_title`：标题可选（默认空字符串）
- `test_create_diary_with_date`：保留日记日期
- `test_create_diary_empty_content`：空内容边界处理
- `test_create_diary_unauthenticated`：未认证请求处理

#### `TestAIErrorHandling` — AI 错误处理
- `test_ai_error_still_saves_diary`：AI 失败仍保存日记，记录错误
- `test_ai_empty_corrections_still_saves`：空修正数组场景（bug 复现）
- `test_ai_401_error_passes_through`：API key 过期错误透传
- `test_ai_success_has_no_error`：成功时 error 字段为 None

#### `TestGetDiaries` — 获取日记
- `test_get_all_diaries`：获取用户所有日记
- `test_get_single_diary`：获取单个日记详情
- `test_get_nonexistent_diary`：获取不存在日记返回 404

#### `TestUpdateDiary` — 更新日记
- `test_update_content_triggers_re_correction`：修改内容触发重新批改
- `test_update_title_only_no_re_correction`：仅改标题不触发 AI

#### `TestDeleteDiary` — 删除日记
- `test_delete_diary`：正常删除
- `test_delete_nonexistent_diary`：删除不存在日记返回 404

### 4. `test_phrase_search.py` — 短语搜索集成测试（流式版本）

> **注意**：短语搜索已改为直接调用大模型，不再使用本地词库，测试已同步更新。

#### `TestSearchPhraseStreamAPI` — 流式 API 测试
- `test_search_phrase_stream_success`：流式 API 返回增量结果（translations → examples → alternatives）
- `test_search_phrase_stream_with_lang_params`：自定义源语言和目标语言参数
- `test_search_phrase_stream_default_lang`：默认语言为中文（`zh`）→ 英语（`en`）

#### `TestSearchPhraseCache` — 缓存功能测试
- `test_cache_hits_second_request`：相同短语第二次请求命中缓存（AI 只调用一次）
- `test_cache_case_insensitive`：缓存不区分大小写（"HELLO" 和 "hello" 视为相同）

#### `TestSearchPhraseStreamErrorHandling` — 错误处理测试
- `test_stream_error_returns_graceful_message`：AI 错误返回友好中文提示
- `test_empty_phrase_rejected`：空短语边界处理

#### `TestSearchPhraseSourceLanguage` — 语言参数测试
- `test_custom_source_lang_fr`：支持自定义源语言（如法语 → 英语）
- `test_default_lang_is_zh_to_en`：默认源语言为中文（`zh`），目标语言为英语（`en`）

### 测试覆盖范围总结

| 模块 | 测试覆盖 | 用例数 |
|------|----------|--------|
| `_parse_json_response()` | 所有解析策略 + 错误场景 + 真实 AI 格式 | 20 |
| POST /api/diaries | 成功、空内容、AI 错误、空结果 | 16 |
| POST /api/search-phrase/stream | 流式响应、错误处理、语言参数 | 8 |
| **总计** | | **44 个通过 + 2 个跳过** |

### 测试运行结果预期

```bash
$ pytest tests/ -v
============================= test session starts ==============================
collected 52 items

tests/test_diary_api.py::TestCreateDiary::test_create_diary_success PASSED
tests/test_diary_api.py::TestCreateDiary::test_create_diary_without_title PASSED
tests/test_diary_api.py::TestCreateDiary::test_create_diary_with_date PASSED
tests/test_diary_api.py::TestCreateDiary::test_create_diary_empty_content PASSED
tests/test_diary_api.py::TestAIErrorHandling::test_ai_error_still_saves_diary PASSED
...
tests/test_json_parsing.py::TestPlainJSON::test_valid_plain_json PASSED
tests/test_json_parsing.py::TestMarkdownCodeBlock::test_json_in_code_block PASSED
...
tests/test_phrase_search.py::TestLocalDictionaryExactMatch::test_exact_match_returns_correct_translations[真是美好的一天] PASSED
...

============================= 52 passed in 3.21s ==============================
```

---

## Docker 部署

```bash
docker-compose up -d
```

---

## 开发约定

### 每次修改后运行测试

```bash
pytest tests/ -v
# 确保所有测试通过后再提交
```

### 技术文档同步

修改功能后，请同步更新 `TECHNICAL_DOC.md`：
- 新增功能 → 添加组件说明
- 修改接口 → 更新 API 表格
- 修复 bug → 记录在「已知问题 & 修复记录」

---

## 持续改进

| 优先级 | 改进方向 |
|--------|----------|
| P1 | 缓存 AI 批改结果，避免重复请求 |
| P2 | 支持导出批改报告 PDF |
| P3 | 用户自定义 AI 提示词模板 |
