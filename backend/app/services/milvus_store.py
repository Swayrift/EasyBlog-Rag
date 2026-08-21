"""向量库抽象接口与 Milvus Lite 实现。

Milvus 记录的主键 id 即 SQLite chunks 表主键（chunk_id），
chunks.milvus_id 保存同一值的字符串形式，用于双向定位。
向量已 L2 归一化，IP 度量等价于余弦相似度。
"""

from __future__ import annotations

import abc
import logging
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class VectorRecord:
    id: int
    embedding: list[float]
    source_type: str
    source_id: int
    title: str


@dataclass
class VectorHit:
    id: int
    score: float
    source_type: str
    source_id: int
    title: str


class VectorStore(abc.ABC):
    """向量库抽象接口，便于替换为其他向量数据库。"""

    @abc.abstractmethod
    def upsert(self, records: list[VectorRecord]) -> None:
        ...

    @abc.abstractmethod
    def delete(self, ids: list[int]) -> None:
        ...

    @abc.abstractmethod
    def search(self, vector: list[float], top_k: int) -> list[VectorHit]:
        ...

    def close(self) -> None:
        return None


class MilvusVectorStore(VectorStore):
    def __init__(self, db_path: str, collection_name: str, dim: int = 1024):
        # 延迟导入：避免在未安装 pymilvus / milvus-lite 时模块级报错，
        # 同时给出清晰的安装提示。
        try:
            from pymilvus import DataType, MilvusClient
        except ImportError as exc:  # pragma: no cover
            raise RuntimeError(
                "pymilvus 未正确安装。向量库需要 pymilvus + milvus-lite，"
                "请先执行 pip install -r requirements.txt。"
            ) from exc

        self._collection = collection_name
        # Milvus Lite 嵌入模式：直接传入本地 .db 文件路径（不是服务 URL），
        # pymilvus 会自动启动 milvus-lite 后端，其余用法与 pymilvus 一致。
        self._client = MilvusClient(db_path)
        self._ensure_collection(DataType, dim)
        self._client.load_collection(collection_name)

    def _ensure_collection(self, DataType, dim: int) -> None:
        if self._client.has_collection(self._collection):
            return
        schema = self._client.create_schema(auto_id=False)
        schema.add_field("id", DataType.INT64, is_primary=True)
        schema.add_field("embedding", DataType.FLOAT_VECTOR, dim=dim)
        schema.add_field("source_type", DataType.VARCHAR, max_length=32)
        schema.add_field("source_id", DataType.INT64)
        schema.add_field("chunk_id", DataType.INT64)
        schema.add_field("title", DataType.VARCHAR, max_length=512)

        index_params = self._client.prepare_index_params()
        index_params.add_index(
            field_name="embedding", index_type="AUTOINDEX", metric_type="IP"
        )
        self._client.create_collection(
            self._collection, schema=schema, index_params=index_params
        )
        logger.info("已创建 Milvus 集合 %s（dim=%d，metric=IP）", self._collection, dim)

    def upsert(self, records: list[VectorRecord]) -> None:
        if not records:
            return
        rows = [
            {
                "id": record.id,
                "chunk_id": record.id,
                "embedding": record.embedding,
                "source_type": record.source_type,
                "source_id": record.source_id,
                "title": record.title[:500],
            }
            for record in records
        ]
        self._client.upsert(collection_name=self._collection, data=rows)

    def delete(self, ids: list[int]) -> None:
        if not ids:
            return
        for start in range(0, len(ids), 500):
            batch = ids[start : start + 500]
            expr = "id in [" + ",".join(str(item) for item in batch) + "]"
            self._client.delete(collection_name=self._collection, filter=expr)

    def search(self, vector: list[float], top_k: int) -> list[VectorHit]:
        results = self._client.search(
            collection_name=self._collection,
            data=[vector],
            anns_field="embedding",
            limit=top_k,
            output_fields=["source_type", "source_id", "title"],
            search_params={"metric_type": "IP"},
        )
        hits: list[VectorHit] = []
        for hit in results[0]:
            entity = hit.get("entity", {})
            hits.append(
                VectorHit(
                    id=int(hit["id"]),
                    score=float(hit["distance"]),
                    source_type=entity.get("source_type", ""),
                    source_id=int(entity.get("source_id", 0)),
                    title=entity.get("title", ""),
                )
            )
        return hits

    def close(self) -> None:
        try:
            self._client.close()
        except Exception:  # noqa: BLE001
            logger.debug("关闭 Milvus 客户端失败", exc_info=True)
