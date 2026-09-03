"""RAG 问答编排：缓存命中 → 查询改写 → 向量检索 → 重排去重 → 组装上下文 → LLM 生成。"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from dataclasses import asdict, dataclass

from sqlmodel import Session, select

from app.core.config import Settings
from app.models.db_models import Chunk, Document, Post
from app.services.embedding import BaseEmbedder
from app.services.llm import LLMClient
from app.services.faiss_store import VectorStore
from app.services.qa_cache import QaCacheService
from app.services.reranker import BaseReranker

logger = logging.getLogger(__name__)


_STREAM_CHUNK_SIZE = 24


def _stage_event(stage: str, label: str) -> dict:
    return {"type": "stage", "stage": stage, "label": label}


def _text_chunks(text: str, size: int = _STREAM_CHUNK_SIZE) -> Iterator[str]:
    for start in range(0, len(text), size):
        chunk = text[start : start + size]
        if chunk:
            yield chunk


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
        qa_cache: QaCacheService | None = None,
    ):
        self._settings = settings
        self._engine = engine
        self._vector_store = vector_store
        self._embedder = embedder
        self._reranker = reranker
        self._llm = llm
        self._qa_cache = qa_cache

    def _extract_question(self, messages: list[dict]) -> str:
        for message in reversed(messages):
            if message.get("role") == "user":
                return str(message.get("content") or "").strip()
        raise ValueError("messages 中没有用户提问")

    def validate_messages(self, messages: list[dict]) -> None:
        self._extract_question(messages)

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

    def _rank_chunks(
        self, query: str, candidates: list[Chunk]
    ) -> tuple[list[ChatSource], list[tuple[str, str]]]:
        """重排候选片段并同时组装来源与 LLM 上下文。"""
        texts = [chunk.content for chunk in candidates]
        ordered: list[tuple[Chunk, float]] = []
        if self._reranker is not None:
            results = self._reranker.rerank(query, texts, self._settings.rerank_top_n)
            seen: set[tuple[str, int, int]] = set()
            for result in results:
                if not (0 <= result.index < len(candidates)):
                    continue
                chunk = candidates[result.index]
                key = (chunk.source_type, chunk.source_id, chunk.chunk_index)
                if key in seen:
                    continue
                seen.add(key)
                ordered.append((chunk, result.score))
        else:
            ordered = [(chunk, 0.0) for chunk in candidates[: self._settings.rerank_top_n]]

        if self._reranker is not None:
            ordered = [
                (chunk, score)
                for chunk, score in ordered
                if score >= self._settings.rerank_min_score
            ]

        # 重排只负责筛选相关片段，最终按文档块主键恢复知识库中的顺序，
        # 让相邻导入的文档内容尽量连续地进入提示词和 sources。
        ordered.sort(key=lambda item: item[0].id if item[0].id is not None else 0)

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
        return sources, contexts

    def chat(self, messages: list[dict]) -> ChatResult:
        question = self._extract_question(messages)

        # 阶段一：问答缓存命中
        cached = self._match_cache(question)
        if cached is not None:
            return cached

        # 1. 查询改写（失败时退回原始问题）
        rewritten = self._llm.rewrite_query(messages)
        query = rewritten or question
        if rewritten:
            logger.info("查询改写：%s -> %s", question, rewritten)

        # 2. 向量检索
        candidates = self._retrieve_chunks(query)
        if not candidates:
            result = ChatResult(answer="知识库中没有检索到相关内容，暂时无法回答这个问题。", sources=[])
            self._maybe_store_cache(question, result)
            return result

        # 3. 重排与去重，随后组装来源与上下文
        sources, contexts = self._rank_chunks(query, candidates)

        # 5. LLM 生成回答（使用原始问题）
        if not self._llm.available:
            answer = "LLM 未配置，仅返回检索到的相关片段，请查看引用来源。"
        else:
            try:
                answer = self._llm.generate_answer(question, contexts)
            except Exception:  # noqa: BLE001
                logger.exception("LLM 生成回答失败")
                answer = "回答生成失败，请稍后重试。以下为检索到的相关片段，可参考引用来源。"

        result = ChatResult(answer=answer, sources=sources)

        # 6. 写入问答缓存
        self._maybe_store_cache(question, result)
        return result

    def chat_stream(self, messages: list[dict]) -> Iterator[dict]:
        """按 RAG 阶段产生 SSE 负载，由 API 层负责编码为事件流。"""
        question = self._extract_question(messages)

        yield _stage_event("cache", "正在读取 FAQ 缓存")
        cached = self._match_cache(question)
        if cached is not None:
            # 缓存命中时没有真实的 LLM 生成，但仍进入回答输出阶段，清除前端状态。
            yield _stage_event("generate", "正在生成回答")
            for chunk in _text_chunks(cached.answer):
                yield {"type": "delta", "content": chunk}
            yield {"type": "sources", "sources": [asdict(source) for source in cached.sources]}
            yield {"type": "done"}
            return

        yield _stage_event("rewrite", "正在进行 Query 改写")
        rewritten = self._llm.rewrite_query(messages)
        query = rewritten or question
        if rewritten:
            logger.info("查询改写：%s -> %s", question, rewritten)

        yield _stage_event("retrieve", "正在检索知识库")
        candidates = self._retrieve_chunks(query)
        if not candidates:
            answer = "知识库中没有检索到相关内容，暂时无法回答这个问题。"
            yield _stage_event("generate", "正在生成回答")
            for chunk in _text_chunks(answer):
                yield {"type": "delta", "content": chunk}
            self._maybe_store_cache(question, ChatResult(answer=answer, sources=[]))
            yield {"type": "sources", "sources": []}
            yield {"type": "done"}
            return

        yield _stage_event("rerank", "正在重排检索结果")
        sources, contexts = self._rank_chunks(query, candidates)
        yield _stage_event("generate", "正在生成回答")

        answer_parts: list[str] = []
        if not self._llm.available:
            answer = "LLM 未配置，仅返回检索到的相关片段，请查看引用来源。"
            for chunk in _text_chunks(answer):
                answer_parts.append(chunk)
                yield {"type": "delta", "content": chunk}
        else:
            try:
                for chunk in self._llm.stream_answer(question, contexts):
                    answer_parts.append(chunk)
                    yield {"type": "delta", "content": chunk}
                answer = "".join(answer_parts).strip()
                if not answer:
                    answer = "回答生成失败，请稍后重试。以下为检索到的相关片段，可参考引用来源。"
                    for chunk in _text_chunks(answer):
                        answer_parts.append(chunk)
                        yield {"type": "delta", "content": chunk}
            except Exception:  # noqa: BLE001
                logger.exception("LLM 流式生成回答失败")
                answer = "回答生成失败，请稍后重试。以下为检索到的相关片段，可参考引用来源。"
                if not answer_parts:
                    for chunk in _text_chunks(answer):
                        answer_parts.append(chunk)
                        yield {"type": "delta", "content": chunk}

        result = ChatResult(answer=answer, sources=sources)
        self._maybe_store_cache(question, result)
        yield {"type": "sources", "sources": [asdict(source) for source in sources]}
        yield {"type": "done"}

    def _match_cache(self, question: str) -> ChatResult | None:
        """阶段一：内存索引按余弦相似度匹配缓存，命中后回库读取答案与来源。"""
        if self._qa_cache is None or self._embedder is None:
            return None
        try:
            self._qa_cache.prune_expired()
        except Exception:  # noqa: BLE001
            logger.warning("清理过期缓存失败", exc_info=True)
        try:
            query_vector = self._embedder.embed([question])[0]
        except Exception:  # noqa: BLE001
            logger.warning("缓存匹配向量化失败，跳过缓存", exc_info=True)
            return None
        hit = self._qa_cache.match(query_vector)
        if hit is None:
            return None
        cache_id, score = hit
        answer, source_dicts = self._qa_cache.get_answer_sources(cache_id)
        sources: list[ChatSource] = []
        for item in source_dicts:
            if isinstance(item, dict):
                try:
                    sources.append(ChatSource(**item))
                except TypeError:
                    continue
        logger.info("问答缓存命中：%s（score=%.4f）", question, score)
        return ChatResult(answer=answer, sources=sources)

    def _maybe_store_cache(self, question: str, result: ChatResult) -> None:
        """阶段二结束：无论回答质量与来源分数如何，都写入缓存。"""
        if self._qa_cache is None or self._embedder is None:
            return
        try:
            query_vector = self._embedder.embed([question])[0]
            source_dicts = [asdict(s) for s in result.sources]
            self._qa_cache.store(question, result.answer, source_dicts, query_vector)
        except Exception:  # noqa: BLE001
            logger.warning("写入问答缓存失败", exc_info=True)
