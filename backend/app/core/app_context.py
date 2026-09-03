"""应用上下文：集中持有配置、数据库引擎与核心服务实例，挂载在 app.state.ctx。"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.engine import Engine

from app.core.config import Settings
from app.services.llm import LLMClient
from app.services.faiss_store import VectorStore
from app.services.rag import RAGService


@dataclass
class AppContext:
    settings: Settings
    engine: Engine
    vector_store: VectorStore | None
    llm: LLMClient
    rag: RAGService
