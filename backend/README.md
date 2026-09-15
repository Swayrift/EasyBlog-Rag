# 博客后端

FastAPI + SQLite（SQLModel）+ FAISS 的个人博客后端，内置 RAG 知识库问答。
向量模型与重排模型使用硅基流动（SiliconFlow）平台的免费模型，答案生成使用 OpenAI 兼容接口（当前配置为 DeepSeek，可在 config.ini 中切换）。

详细设计见 `../docs/design.md`。

## 环境要求

- Python 3.10 及以上。
- 向量库使用本地 FAISS CPU 索引，索引文件位于 `data/faiss/`，无需单独部署服务。
- 如果使用当前的 venv + pip 流程，请先在目标平台验证 `faiss-cpu` 的安装和
  `import faiss` 冒烟测试。
- 代码里已做降级处理：向量库不可用时，博客的文章/标签/关于我接口仍然可用，
  仅问答检索不可用。

## 快速开始（venv）

在 `backend/` 目录下执行：

```bash
# 1. 创建并激活虚拟环境
python -m venv .venv
# Windows:
.venv\Scripts\activate
# Linux / macOS / WSL:
source .venv/bin/activate

# 2. 安装依赖
pip install -r requirements.txt

# 3. 准备配置
#    在 [siliconflow] 填入 api_key；如需生成回答，再在 [openai] 填入 api_key
cp config.example.ini config.ini   # 如 config.ini 不存在

# 4. 启动（启动时会自动执行知识导入与增量同步）
python -m app.main
# 或
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

知识导入与增量同步只在服务启动时执行，没有独立的手动导入入口。改完 `../content/` 下的文件后，重启后端即可生效（未变更的文件按哈希跳过，不会重复消耗向量化）。

## 配置说明（config.ini）

| 节 | 说明 |
| :-- | :-- |
| app | 站点标题、监听地址端口、CORS 允许来源 |
| database / faiss | SQLite 与 FAISS 索引、清单文件路径、向量维度（1024） |
| content | 文章、本地文档、关于我文件的位置 |
| import | Markdown 结构化切块的最小长度、软上限、硬上限，以及 embedding 批大小与批间隔（免费档限流保护） |
| retrieval | 向量召回 top_k、重排保留 rerank_top_n、重排最低置信度 min_score |
| qa_cache | 问答缓存：命中阈值 similarity_threshold、有效期 cache_ttl（秒）；启动时载入未过期条目，过期条目在后续读取缓存时清理 |
| siliconflow | API Key、模型名（BAAI/bge-m3、BAAI/bge-reranker-v2-m3） |
| openai | OpenAI 兼容接口（当前配置为 DeepSeek）：base_url、API Key、模型、温度；api_key 留空则问答只返回检索片段 |

`config.ini` 含密钥，已被 `.gitignore` 排除；`config.example.ini` 为可提交模板。

## 接口一览

| 方法 | 路径 | 说明 |
| :-- | :-- | :-- |
| GET | /api/posts?page=1&page_size=10&tag=标签名 | 文章列表 |
| GET | /api/posts/{slug} | 文章详情 |
| GET | /api/posts/id/{post_id} | 按 ID 查文章，供问答引用来源跳转 |
| GET | /api/tags | 标签列表（含已发布文章数） |
| GET | /api/about | 关于我 |
| POST | /api/chat | 知识库问答，SSE 流式返回（请求体为 OpenAI 兼容 messages 数组） |

接口文档：启动后访问 `/docs`（Swagger UI）。

## 内容管理

- 文章：放入 `../content/posts/`，front matter 支持 `title / slug / summary / tags / status / created_at`。
- 本地文档：放入 `../content/documents/`，不带 front matter，自动取首个一级标题为标题（无则回退文件名）。
- 关于我：`../content/about.md`，front matter 支持 `name / summary / tech_stack / contact`。
- 每次启动自动增量同步：按文件哈希判断是否变更，未变跳过，变化则重建向量，磁盘删除则真删除记录与向量。

## 目录结构

```text
backend/
├── app/
│   ├── main.py            # 应用入口，启动时自动导入知识
│   ├── api/               # 路由：posts/tags/about/chat
│   ├── core/              # 配置、数据库、日志、应用上下文
│   ├── models/            # SQLite 表模型（SQLModel）
│   ├── schemas/           # 请求/响应模型（Pydantic）
│   └── services/          # 硅基流动客户端、FAISS、导入器、问答缓存、RAG 编排
├── data/                  # 运行期数据：blog.db、faiss/（不入库）
├── config.ini             # 实际配置（含密钥，不入库）
├── config.example.ini
└── requirements.txt
```
