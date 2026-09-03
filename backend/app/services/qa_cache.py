"""问答缓存服务。

内存中仅保存「问题 + 问题向量」，用于避免为逐个比对频繁读库；
命中后再按缓存 id 从 SQLite 读取 answer 与 sources。
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timedelta

from sqlmodel import Session, select, delete

from app.core.config import Settings
from app.models.db_models import QaCache
from app.services.embedding import BaseEmbedder

logger = logging.getLogger(__name__)


def _cosine(a: list[float], b: list[float]) -> float:
    """向量已做 L2 归一化，点积即余弦相似度。"""
    dot = sum(x * y for x, y in zip(a, b))
    return max(-1.0, min(1.0, dot))


class QaCacheService:
    def __init__(self, settings: Settings, engine, embedder: BaseEmbedder | None):
        self._settings = settings
        self._engine = engine
        self._embedder = embedder
        self._index: list[tuple[int, list[float]]] = []  # (cache_id, question_vector)

    def load(self) -> None:
        """启动时载入未过期的条目（仅问题向量）。"""
        self._index.clear()
        if self._embedder is None:
            return
        now = datetime.now()
        with Session(self._engine) as session:
            rows = session.exec(select(QaCache)).all()
        for row in rows:
            if row.expires_at is not None and row.expires_at <= now:
                continue
            try:
                vector = json.loads(row.question_vector)
            except (ValueError, TypeError):
                continue
            if not isinstance(vector, list) or not vector:
                continue
            self._index.append((row.id, vector))
        logger.info("载入问答缓存 %d 条", len(self._index))

    def clear(self) -> None:
        """清空 SQLite 中的全部缓存问答及内存匹配索引。"""
        with Session(self._engine) as session:
            rows = session.exec(select(QaCache)).all()
            for row in rows:
                session.delete(row)
            if rows:
                session.commit()
        self._index.clear()
        logger.info("已清空问答缓存 %d 条", len(rows))

    def match(self, query_vector: list[float]) -> tuple[int, float] | None:
        """返回 (cache_id, score)，若最高相似度低于阈值则返回 None。"""
        best: tuple[int, float] | None = None
        for cache_id, vector in self._index:
            score = _cosine(query_vector, vector)
            if best is None or score > best[1]:
                best = (cache_id, score)
        if best is None or best[1] < self._settings.qa_similarity_threshold:
            return None
        return best

    def get_answer_sources(self, cache_id: int) -> tuple[str, list[dict]]:
        """命中后回库读取 answer 与 sources。"""
        with Session(self._engine) as session:
            row = session.get(QaCache, cache_id)
        if row is None:
            return "", []
        try:
            sources = json.loads(row.sources)
        except (ValueError, TypeError):
            sources = []
        if not isinstance(sources, list):
            sources = []
        return row.answer, sources

    def store(
        self,
        question: str,
        answer: str,
        sources: list[dict],
        question_vector: list[float],
    ) -> None:
        """写入缓存并同步追加内存索引。"""
        expires_at = datetime.now() + timedelta(seconds=self._settings.qa_cache_ttl)
        with Session(self._engine) as session:
            row = QaCache(
                question=question,
                answer=answer,
                sources=json.dumps(sources, ensure_ascii=False),
                question_vector=json.dumps(question_vector),
                # status="active",
                expires_at=expires_at,
            )
            session.add(row)
            session.commit()
            session.refresh(row)
            cache_id = row.id
        self._index.append((cache_id, question_vector))

    def prune_expired(self) -> None:
        """清理已过期条目：直接物理删除（数据库 + 内存索引）"""
        now = datetime.now()
        with Session(self._engine) as session:
            rows = session.exec(select(QaCache)).all()
            expired_ids = set()
            for row in rows:
                if row.expires_at is not None and row.expires_at <= now:
                    expired_ids.add(row.id)
            if expired_ids:
                session.exec(delete(QaCache).where(QaCache.id.in_(expired_ids)))
                session.commit()
        if expired_ids:
            self._index = [(cid, vec) for cid, vec in self._index if cid not in expired_ids]
            logger.info("清理过期问答缓存 %d 条", len(expired_ids))
