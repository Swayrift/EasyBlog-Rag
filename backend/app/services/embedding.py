"""Embedding 抽象接口与硅基流动（BAAI/bge-m3）实现。"""

from __future__ import annotations

import abc
import logging
import math
import time

from app.services.http_utils import build_client, post_with_retry

logger = logging.getLogger(__name__)


class BaseEmbedder(abc.ABC):
    """文本向量化抽象接口，便于替换为其他向量模型服务。"""

    @abc.abstractmethod
    def embed(self, texts: list[str]) -> list[list[float]]:
        """批量向量化，返回与输入顺序一致的向量列表。"""


def l2_normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm == 0:
        return vector
    return [value / norm for value in vector]


class SiliconFlowEmbedder(BaseEmbedder):
    """硅基流动 POST /v1/embeddings（OpenAI 兼容格式）。

    输出向量统一做 L2 归一化，配合 Milvus 的 IP 度量等价于余弦相似度。
    """

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str = "https://api.siliconflow.cn",
        batch_size: int = 16,
        batch_sleep: float = 0.5,
        timeout: float = 80.0,
    ):
        self.model = model
        self.batch_size = max(1, batch_size)
        self.batch_sleep = max(0.1, batch_sleep)
        self._client = build_client(api_key, base_url, timeout)

    def embed(self, texts: list[str]) -> list[list[float]]:
        texts = [text.strip() for text in texts]
        vectors: list[list[float]] = []
        for start in range(0, len(texts), self.batch_size):
            batch = texts[start : start + self.batch_size]
            data = post_with_retry(
                self._client,
                "/v1/embeddings",
                {"model": self.model, "input": batch},
            )
            items = sorted(data["data"], key=lambda item: item.get("index", 0))
            vectors.extend(l2_normalize(item["embedding"]) for item in items)
            if start + self.batch_size < len(texts) and self.batch_sleep > 0:
                time.sleep(self.batch_sleep)  # 免费档限流保护
        return vectors

    def close(self) -> None:
        self._client.close()
