"""RAG 问答编排：查询改写 → 向量检索 → 重排去重 → 组装上下文 → LLM 生成。"""

from __future__ import annotations

import logging
from dataclasses import dataclass

from sqlmodel import Session, select

from app.core.config import Settings
from app.models.db_models import Chunk, Document, Post
from app.services.embedding import BaseEmbedder
from app.services.llm import LLMClient
from app.services.milvus_store import VectorStore
from app.services.reranker import BaseReranker

logger = logging.getLogger(__name__)


@dataclass
class ChatSource:
    title: str
    source_type: str
    source_id: int
    chunk: str
    score: float


@dataclass
class ChatResult:
    answer: str
    sources: list[ChatSource]


class RAGService:
    def __init__(
        self,
        settings: Settings,
        engine,
        vector_store: VectorStore | None,
        embedder: BaseEmbedder | None,
        reranker: BaseReranker | None,
        llm: LLMClient,
    ):
        self._settings = settings
        self._engine = engine
        self._vector_store = vector_store
        self._embedder = embedder
        self._reranker = reranker
        self._llm = llm

    def _extract_question(self, messages: list[dict]) -> str:
        for message in reversed(messages):
            if message.get("role") == "user":
                return str(message.get("content") or "").strip()
        raise ValueError("messages 中没有用户提问")

    def _retrieve_chunks(self, query: str) -> list[Chunk]:
        if self._vector_store is None or self._embedder is None:
            return []
        vector = self._embedder.embed([query])[0]
        hits = self._vector_store.search(vector, self._settings.top_k)
        if not hits:
            return []
        chunk_ids = [hit.id for hit in hits]
        with Session(self._engine) as session:
            chunks = session.exec(select(Chunk).where(Chunk.id.in_(chunk_ids))).all()
        by_id = {chunk.id: chunk for chunk in chunks}
        return [by_id[chunk_id] for chunk_id in chunk_ids if chunk_id in by_id]

    def _resolve_title(self, chunk: Chunk) -> str:
        with Session(self._engine) as session:
            if chunk.source_type == "post":
                post = session.get(Post, chunk.source_id)
                return post.title if post else "未知文章"
            doc = session.get(Document, chunk.source_id)
            return doc.title if doc else "未知文档"

    def chat(self, messages: list[dict]) -> ChatResult:
        question = self._extract_question(messages)

        # 1. 查询改写（失败时退回原始问题）
        rewritten = self._llm.rewrite_query(messages)
        query = rewritten or question
        if rewritten:
            logger.info("查询改写：%s -> %s", question, rewritten)

        # 2. 向量检索
        candidates = self._retrieve_chunks(query)
        if not candidates:
            return ChatResult(answer="知识库中没有检索到相关内容，暂时无法回答这个问题。", sources=[])

        # 3. 重排与去重
        texts = [chunk.content for chunk in candidates]
        if self._reranker is not None:
            results = self._reranker.rerank(query, texts, self._settings.rerank_top_n)
            ordered = []
            seen: set[int] = set()
            for result in results:
                if 0 <= result.index < len(candidates) and result.index not in seen:
                    seen.add(result.index)
                    ordered.append((candidates[result.index], result.score))
        else:
            ordered = [(chunk, 0.0) for chunk in candidates[: self._settings.rerank_top_n]]

        # 4. 组装来源与上下文
        sources: list[ChatSource] = []
        contexts: list[tuple[str, str]] = []
        for chunk, score in ordered:
            title = self._resolve_title(chunk)
            sources.append(
                ChatSource(
                    title=title,
                    source_type=chunk.source_type,
                    source_id=chunk.source_id,
                    chunk=chunk.content,
                    score=round(score, 4),
                )
            )
            contexts.append((title, chunk.content))

        # 5. LLM 生成回答（使用原始问题，符合设计稿 7.2）
        if not self._llm.available:
            answer = "LLM 未配置，仅返回检索到的相关片段，请查看引用来源。"
        else:
            try:
                answer = self._llm.generate_answer(question, contexts)
            except Exception:  # noqa: BLE001
                logger.exception("LLM 生成回答失败")
                answer = "回答生成失败，请稍后重试。以下为检索到的相关片段，可参考引用来源。"

        return ChatResult(answer=answer, sources=sources)
