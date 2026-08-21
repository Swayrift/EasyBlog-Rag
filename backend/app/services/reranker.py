"""Reranker 抽象接口与硅基流动（BAAI/bge-reranker-v2-m3）实现。"""

from __future__ import annotations

import abc
import logging
from dataclasses import dataclass

from app.services.http_utils import build_client, post_with_retry

logger = logging.getLogger(__name__)


@dataclass
class RerankResult:
    index: int
    score: float


class BaseReranker(abc.ABC):
    """重排序抽象接口。"""

    @abc.abstractmethod
    def rerank(self, query: str, documents: list[str], top_n: int) -> list[RerankResult]:
        """返回按相关性降序排列的重排结果。"""


class SiliconFlowReranker(BaseReranker):
    """硅基流动 POST /v1/rerank。"""

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str = "https://api.siliconflow.cn",
        timeout: float = 60.0,
    ):
        self.model = model
        self._client = build_client(api_key, base_url, timeout)

    def rerank(self, query: str, documents: list[str], top_n: int) -> list[RerankResult]:
        documents = [doc.strip() for doc in documents]
        if not query.strip() or not documents:
            return []
        payload = {
            "model": self.model,
            "query": query.strip(),
            "documents": documents,
            "top_n": max(1, min(top_n, len(documents))),
            "return_documents": False,
        }
        data = post_with_retry(self._client, "/v1/rerank", payload)
        results = [
            RerankResult(index=int(item["index"]), score=float(item["relevance_score"]))
            for item in data.get("results", [])
        ]
        results.sort(key=lambda item: item.score, reverse=True)
        return results

    def close(self) -> None:
        self._client.close()
