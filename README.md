# AI 文档问答助手 (RAG Document Q&A)

基于 **LangGraph + FastAPI + Next.js** 的智能文档问答系统，支持多格式文档上传、混合检索（Dense + BM25 + Reranker）、多轮对话、联网搜索与长期记忆。

---

## 项目结构

```
├── backend/                    # FastAPI 后端
│   ├── app/
│   │   ├── api/v1/             # REST API：auth、chat、documents、api_keys
│   │   ├── chat/               # LangGraph 对话流程图
│   │   ├── core/               # 配置 (Pydantic Settings) 与安全模块
│   │   ├── db/                 # SQLAlchemy 数据库会话
│   │   ├── evaluation/         # 评测框架（32 项聚合指标）
│   │   ├── models/             # ORM 模型
│   │   ├── rag/                # RAG 检索流水线
│   │   ├── repositories/       # 数据访问层
│   │   ├── schemas/            # Pydantic 请求/响应模型
│   │   ├── services/           # 业务服务（LLM、Auth、文档、联网搜索等）
│   │   └── utils/              # 工具函数
│   ├── data/                   # 运行时数据（SQLite、ChromaDB）
│   ├── logs/                   # 应用日志
│   ├── uploads/                # 用户上传文件
│   └── requirements.txt
│
├── frontend-rag-web-ui/        # Next.js 前端
│   └── src/
│       ├── app/                # 页面：登录、注册、仪表盘、对话、知识库、评测
│       ├── components/         # UI 组件（shadcn/ui + Radix UI）
│       └── lib/                # API 客户端与工具函数
│
└── .gitignore                  # 根级忽略规则
```

---

## 功能特性

- **文档问答** — 上传 PDF / TXT / Markdown / DOCX / PPTX / XLSX / HTML，基于文档内容精准回答
- **混合检索** — Dense 向量 + BM25 稀疏 → RRF 融合 → Reranker 重排序
- **智能路由** — 意图分类自动判断：知识库问答 / 专业问题 / 普通聊天 / 文档总结 / 追问
- **查询改写** — 检索不足时 LLM 自动改写查询重试
- **流式输出** — SSE 实时推送回答内容
- **多轮对话** — LangGraph 管理对话流程，支持上下文记忆
- **联网搜索** — 可选 Tavily 联网增强（通过 `.env` 开启）
- **长期记忆** — 可选 Mem0 跨会话记忆（通过 `.env` 开启）
- **用户系统** — JWT 认证 + API Key 管理
- **评测框架** — 32 项指标：检索召回率、意图准确率、生成质量、延迟、Token 用量等

---

## 快速开始

### 环境要求

- **Python** ≥ 3.11
- **Node.js** ≥ 18 + **pnpm**

### 1. 克隆仓库

```bash
git clone <repo-url>
cd my_program
```

### 2. 配置后端

```bash
cd backend

# 创建虚拟环境
python -m venv .venv
.venv\Scripts\activate   # Windows
# source .venv/bin/activate  # macOS / Linux

# 安装依赖
pip install -r requirements.txt
```

### 3. 配置环境变量

在 `backend/` 下创建 `.env` 文件：

```env
# ---- 必填 ----
LLM_API_KEY=sk-your-key-here
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL=gpt-4o-mini

# ---- 可选：联网搜索 ----
WEB_SEARCH_ENABLED=true
TAVILY_API_KEY=tvly-your-key

# ---- 可选：长期记忆 ----
MEM0_ENABLED=true
MEM0_LLM_API_KEY=sk-your-key
MEM0_LLM_MODEL=gpt-4o-mini
MEM0_EMBEDDER_API_KEY=sk-your-key
MEM0_EMBEDDER_MODEL=text-embedding-3-small
MEM0_EMBEDDING_DIMS=1536

# ---- 可选：自定义 ----
# JWT_SECRET_KEY=change-me-in-production
# JWT_EXPIRE_MINUTES=1440
```

### 4. 启动后端

```bash
cd backend
uvicorn app.main:app --reload --port 8000
```

API 文档自动生成：http://localhost:8000/docs

### 5. 启动前端

```bash
cd frontend-rag-web-ui
pnpm install
pnpm dev
```

打开 http://localhost:3000 即可使用。

---

## API 概览

所有 API 挂载于 `/api/v1`：

| 模块 | 端点 | 说明 |
|------|------|------|
| **Auth** | `POST /auth/register` | 用户注册 |
| | `POST /auth/login` | 用户登录（返回 JWT） |
| **Chat** | `GET /chat/conversations` | 列出会话 |
| | `POST /chat/query` | 同步问答 |
| | `POST /chat/stream/query` | SSE 流式问答 |
| **Documents** | `POST /documents/upload` | 上传文档 |
| | `GET /documents` | 列出文档 |
| | `DELETE /documents/{id}` | 删除文档 |
| **API Keys** | `POST /api-keys` | 创建 API Key |
| | `GET /api-keys` | 列出 API Keys |
| | `DELETE /api-keys/{id}` | 删除 API Key |
| **Evaluation** | `/evaluation/*` | 评测数据集 & 运行管理 |
| **Health** | `GET /api/health` | 健康检查 |

---

## 技术栈

### 后端

| 组件 | 技术 |
|------|------|
| Web 框架 | FastAPI |
| 数据库 | SQLite + SQLAlchemy |
| 向量存储 | ChromaDB |
| 对话编排 | LangGraph |
| 嵌入 / LLM | OpenAI 兼容 API |
| 关键词检索 | BM25 (rank-bm25) |
| 文档解析 | PyPDF + MarkItDown |
| 认证 | JWT (python-jose) |

### 前端

| 组件 | 技术 |
|------|------|
| 框架 | Next.js 14 + React 18 |
| 样式 | Tailwind CSS 3 |
| 组件库 | shadcn/ui + Radix UI |
| 语言 | TypeScript 5 |

---

## RAG 检索流程

```
用户提问
  ↓
意图分类（问候 / 知识库 / 专业 / 普通 / 追问 / 文档总结）
  ↓
Dense 检索 + BM25 检索
  ↓
RRF 融合 → Top-K 候选
  ↓
Reranker 重排序（语义 + n-gram + 排名）
  ↓
LLM 判断是否充分 → [充分] 生成回答
                    → [不足] 改写查询重试（最多 2 次）
                    → [无结果] 兜底回复 / 联网搜索
```

---

## 评测

后端内置评测框架，支持：

- **检索指标**：Recall@5/10、Precision@5、MRR、NDCG@5
- **混合检索分析**：Dense-Only / BM25-Only / Hybrid / Reranker 增益
- **生成质量**：忠实度、相关性、正确性、完整性（LLM Judge）
- **意图准确率** + 混淆矩阵
- **性能**：延迟 (avg/P50/P95)、Token 用量
- **拒答质量**：Precision / Recall

通过前端 Dashboard → Evaluation 页面或 API 使用。

---

## License

MIT