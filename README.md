# SwayRift 个人博客

极简、可扩展的个人技术博客，内置 RAG 知识库问答：文章与本地文档经切分、向量化后存入
FAISS，提问时先检索再生成，回答附带引用来源。

- 后端：FastAPI + SQLite（SQLModel）+ FAISS，详见 [`backend/README.md`](backend/README.md)
- 前端：Vue 3 + Vite + Vue Router，黑色 × 橙色编辑风格主题，详见 [`frontend/README.md`](frontend/README.md)
- 设计文档：[`docs/design.md`](docs/design.md)
- 内容：Markdown 文件存放在 `content/`（posts / documents / about.md），后端启动时自动增量同步

## 快速开始

后端（Python 3.10+，venv）：

```bash
cd backend
python -m venv .venv && .venv\Scripts\activate   # Windows
pip install -r requirements.txt
cp config.example.ini config.ini                 # 填入硅基流动与 LLM 密钥
python -m app.main                               # http://127.0.0.1:8000
```

前端（另开终端）：

```bash
cd frontend
npm install
npm run dev                                      # http://localhost:5173，/api 已代理到 8000
```

浏览器打开 http://localhost:5173 即可。生产部署为 `npm run build` 后由 Nginx 托管
`dist/` 并反代 `/api`，详见设计文档 §12。

## 依赖的第三方服务

- 硅基流动（SiliconFlow）：BAAI/bge-m3 向量召回 + BAAI/bge-reranker-v2-m3 重排，免费额度
- LLM：OpenAI 兼容接口（当前配置为 DeepSeek），在 `backend/config.ini` 的 `[openai]` 节切换

密钥均放在 `backend/config.ini`（不入仓库），模板见 `backend/config.example.ini`。
