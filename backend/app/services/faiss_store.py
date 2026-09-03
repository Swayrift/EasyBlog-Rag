"""FAISS 本地向量索引实现。

SQLite 是 Chunk 与来源元数据的事实来源，FAISS 只保存向量和 Chunk ID。
Embedding 已在上游做 L2 归一化，因此 IndexFlatIP 等价于余弦相似度。
"""

from __future__ import annotations

import abc
import json
import logging
import os
import threading
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)

_INDEX_SCHEMA_VERSION = 2


@dataclass
class VectorRecord:
    id: int
    embedding: list[float]
    source_type: str
    source_id: int
    chunk_index: int


@dataclass
class VectorHit:
    id: int
    score: float
    source_type: str = ""
    source_id: int = 0
    chunk_index: int = 0


class VectorStore(abc.ABC):
    """向量库抽象接口，便于替换本地索引实现。"""

    @abc.abstractmethod
    def upsert(self, records: list[VectorRecord]) -> None:
        ...

    @abc.abstractmethod
    def delete(self, ids: list[int]) -> None:
        ...

    @abc.abstractmethod
    def search(self, vector: list[float], top_k: int) -> list[VectorHit]:
        ...

    @property
    def needs_rebuild(self) -> bool:
        return False

    def mark_rebuild(self) -> None:
        return None

    def has_ids(self, ids: list[int]) -> bool:
        return True

    def persist(self) -> None:
        return None

    def close(self) -> None:
        self.persist()


class FaissVectorStore(VectorStore):
    """使用显式 Chunk ID 的精确 Inner Product 索引。"""

    def __init__(self, index_path: str | Path, manifest_path: str | Path, dim: int = 1024):
        try:
            import faiss
            import numpy as np
        except ImportError as exc:  # pragma: no cover - 依赖缺失时由启动层降级
            raise RuntimeError(
                "FAISS 未正确安装，请先安装 faiss-cpu 与 numpy。"
            ) from exc

        self._faiss = faiss
        self._np = np
        self._path = Path(index_path)
        self._manifest_path = Path(manifest_path)
        self._dim = dim
        self._lock = threading.RLock()
        self._dirty = False
        self._needs_rebuild = False
        self._path.parent.mkdir(parents=True, exist_ok=True)
        self._manifest_path.parent.mkdir(parents=True, exist_ok=True)

        tmp_path = self._path.with_name(f"{self._path.name}.tmp")
        if not self._path.exists() and tmp_path.exists():
            # 上次进程可能在原子替换前退出，优先恢复完整的临时索引。
            try:
                os.replace(tmp_path, self._path)
            except OSError:
                logger.warning("无法恢复 FAISS 临时索引：%s", tmp_path)

        if self._path.exists():
            try:
                self._index = faiss.read_index(str(self._path))
                self._validate_index()
                if not self._manifest_path.exists():
                    self._needs_rebuild = True
                else:
                    manifest = json.loads(self._manifest_path.read_text(encoding="utf-8"))
                    if manifest.get("schema_version") != _INDEX_SCHEMA_VERSION:
                        self._needs_rebuild = True
            except Exception as exc:  # noqa: BLE001
                logger.warning("FAISS 索引不可用，将在启动同步时重建：%s", exc)
                self._index = self._new_index()
                self._needs_rebuild = True
        else:
            self._index = self._new_index()
            self._needs_rebuild = True

    def _new_index(self):
        return self._faiss.IndexIDMap2(self._faiss.IndexFlatIP(self._dim))

    def _validate_index(self) -> None:
        if int(self._index.d) != self._dim:
            raise ValueError(
                f"FAISS 索引维度为 {self._index.d}，配置维度为 {self._dim}"
            )
        if int(self._index.metric_type) != int(self._faiss.METRIC_INNER_PRODUCT):
            raise ValueError("FAISS 索引度量不是 Inner Product")

    def _validate_vectors(self, vectors) -> None:
        if vectors.ndim != 2 or vectors.shape[1] != self._dim:
            raise ValueError(
                f"向量维度错误：收到 {vectors.shape}，期望 (*, {self._dim})"
            )
        if not self._np.isfinite(vectors).all():
            raise ValueError("向量包含 NaN 或无穷值")

    @property
    def needs_rebuild(self) -> bool:
        return self._needs_rebuild

    def mark_rebuild(self) -> None:
        self._needs_rebuild = True

    def has_ids(self, ids: list[int]) -> bool:
        with self._lock:
            if not ids:
                return True
            if self._index.ntotal == 0:
                return False
            indexed_ids = self._faiss.vector_to_array(self._index.id_map)
            return set(int(item) for item in ids).issubset(
                set(int(item) for item in indexed_ids)
            )

    def upsert(self, records: list[VectorRecord]) -> None:
        if not records:
            return
        with self._lock:
            # 同一批次内保留最后一次记录，避免重复 ID。
            deduped = {record.id: record for record in records}
            vectors = self._np.asarray(
                [record.embedding for record in deduped.values()], dtype="float32"
            )
            ids = self._np.asarray(list(deduped), dtype="int64")
            self._validate_vectors(vectors)
            self._index.remove_ids(ids)
            self._index.add_with_ids(vectors, ids)
            self._dirty = True

    def delete(self, ids: list[int]) -> None:
        if not ids:
            return
        with self._lock:
            self._index.remove_ids(self._np.asarray(ids, dtype="int64"))
            self._dirty = True

    def search(self, vector: list[float], top_k: int) -> list[VectorHit]:
        if top_k <= 0:
            return []
        with self._lock:
            if self._index.ntotal == 0:
                return []
            query = self._np.asarray([vector], dtype="float32")
            self._validate_vectors(query)
            limit = min(int(top_k), int(self._index.ntotal))
            distances, labels = self._index.search(query, limit)
            return [
                VectorHit(id=int(vector_id), score=float(score))
                for score, vector_id in zip(distances[0], labels[0])
                if int(vector_id) >= 0
            ]

    def persist(self) -> None:
        with self._lock:
            if not self._dirty and self._path.exists() and self._manifest_path.exists():
                return
            tmp_path = self._path.with_name(f"{self._path.name}.tmp")
            self._faiss.write_index(self._index, str(tmp_path))
            with open(tmp_path, "r+b") as handle:
                os.fsync(handle.fileno())
            os.replace(tmp_path, self._path)
            manifest = {
                "schema_version": _INDEX_SCHEMA_VERSION,
                "dimension": self._dim,
                "metric": "IP",
                "index_type": "IndexIDMap2(IndexFlatIP)",
                "vector_count": int(self._index.ntotal),
            }
            manifest_tmp = self._manifest_path.with_name(
                f"{self._manifest_path.name}.tmp"
            )
            manifest_tmp.write_text(
                json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8"
            )
            with open(manifest_tmp, "r+b") as handle:
                os.fsync(handle.fileno())
            os.replace(manifest_tmp, self._manifest_path)
            self._dirty = False
            self._needs_rebuild = False
            logger.info("FAISS 索引已保存：%s（%d 条）", self._path, self._index.ntotal)
