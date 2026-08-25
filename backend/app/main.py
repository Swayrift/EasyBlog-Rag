"""FastAPI 应用入口。

启动时自动初始化数据库与向量库，并执行知识导入（解析文章与本地文档）。
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import about, chat, health, posts, tags
from app.core.app_context import AppContext
from app.core.config import Settings, load_settings
from app.core.database import create_db_engine, init_db
from app.core.logging import setup_logging
from app.services.embedding import BaseEmbedder, SiliconFlowEmbedder
from app.services.importer import sync_knowledge
from app.services.llm import LLMClient
from app.services.milvus_store import MilvusVectorStore, VectorStore
from app.services.qa_cache import QaCacheService
from app.services.rag import RAGService
from app.services.reranker import BaseReranker, SiliconFlowReranker

logger = logging.getLogger(__name__)


def _build_vector_services(settings: Settings) -> tuple[VectorStore | None, BaseEmbedder | None, BaseReranker | None]:
    """初始化向量库与硅基流动模型客户端；失败时降级为不可用而非直接崩溃。"""
    try:
        embedder: BaseEmbedder = SiliconFlowEmbedder(
            api_key=settings.sf_api_key,
            model=settings.embedding_model,
            base_url=settings.sf_base_url,
            batch_size=settings.embedding_batch_size,
            batch_sleep=settings.batch_sleep,
            timeout=settings.sf_timeout,
        )
        reranker: BaseReranker = SiliconFlowReranker(
            api_key=settings.sf_api_key,
            model=settings.reranker_model,
            base_url=settings.sf_base_url,
            timeout=settings.sf_timeout,
        )
    except Exception:  # noqa: BLE001
        logger.exception("硅基流动客户端初始化失败，问答检索不可用")
        return None, None, None

    try:
        settings.milvus_db_path.parent.mkdir(parents=True, exist_ok=True)
        vector_store: VectorStore = MilvusVectorStore(
            db_path=str(settings.milvus_db_path),
            collection_name=settings.collection_name,
            dim=settings.embedding_dim,
        )
    except Exception:  # noqa: BLE001
        logger.exception(
            "Milvus Lite 初始化失败，问答检索不可用。"
            "请确认已安装 pymilvus 与 milvus-lite（pip install -r requirements.txt），"
            "且本地 .db 文件所在目录可写。"
        )
        return None, embedder, reranker

    return vector_store, embedder, reranker


def _run_initial_import(settings: Settings, engine, vector_store, embedder) -> None:
    # 导入器已支持降级：向量服务不可用时仍会同步 SQLite 元数据，仅跳过向量化。
    try:
        sync_knowledge(settings, engine, vector_store, embedder)
    except Exception:  # noqa: BLE001
        logger.exception("启动时的知识导入失败")


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = load_settings()
    setup_logging(settings.debug)
    logger.info("启动 %s", settings.title)

    engine = create_db_engine(settings)
    init_db(engine)

    vector_store, embedder, reranker = _build_vector_services(settings)
    llm = LLMClient(
        api_key=settings.openai_api_key,
        model=settings.llm_model,
        base_url=settings.openai_base_url,
        temperature=settings.llm_temperature,
    )
    if not llm.available:
        logger.warning("未配置 OpenAI API Key，问答将只返回检索片段而不生成回答")

    _run_initial_import(settings, engine, vector_store, embedder)

    qa_cache = QaCacheService(settings=settings, engine=engine, embedder=embedder)
    qa_cache.clear()
    qa_cache.load()

    rag = RAGService(
        settings=settings,
        engine=engine,
        vector_store=vector_store,
        embedder=embedder,
        reranker=reranker,
        llm=llm,
        qa_cache=qa_cache,
    )
    app.state.ctx = AppContext(
        settings=settings,
        engine=engine,
        vector_store=vector_store,
        llm=llm,
        rag=rag,
    )

    yield

    if vector_store is not None:
        vector_store.close()
    if embedder is not None:
        embedder.close()
    if reranker is not None:
        reranker.close()
    engine.dispose()
    logger.info("已退出")


def create_app() -> FastAPI:
    settings = load_settings()
    app = FastAPI(title=settings.title, lifespan=lifespan)

    if settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(settings.cors_origins),
            allow_credentials=False,
            allow_methods=["*"],
            allow_headers=["*"],
        )

    app.include_router(health.router)
    app.include_router(posts.router)
    app.include_router(tags.router)
    app.include_router(about.router)
    app.include_router(chat.router)
    return app


app = create_app()


def main() -> None:
    import uvicorn

    settings = load_settings()
    setup_logging(settings.debug)
    uvicorn.run("app.main:app", host=settings.host, port=settings.port, reload=settings.debug)


if __name__ == "__main__":
    main()
