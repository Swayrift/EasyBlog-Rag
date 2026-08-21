"""正文切分：embedding 语义分块 + 最小/最大字符数约束。

按句号"。"与换行符（\n / \n\n）提取句子，用向量模型计算相邻句子的相似度：
- 相邻句子相似度突然下降，且当前 chunk 已达到最低字符数时，认为话题发生切换，
  此处切分为一个 chunk；
- 无论是否遇到语义边界，chunk 累计超过最大字符数时按句子截止，
  保留能容纳的最多句子，然后进入下一个 chunk。

注：原 overlap 逻辑在新的按句子切分策略下不再适用，因此不再使用。
"""

from __future__ import annotations

import logging
import math
import re

from app.services.embedding import BaseEmbedder

logger = logging.getLogger(__name__)


def _split_sentences(text: str) -> list[str]:
    """按句号切分句子，句号保留在句末"""
    sentences: list[str] = []
    for piece in re.split(r'(?<=[。.！？!?])', text):
        sentence = re.sub(r"\s+", " ", piece).strip()
        if sentence:
            sentences.append(sentence)
    return sentences


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if len(a) != len(b):
        raise ValueError("向量维度不一致，无法计算相似度")
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return max(-1.0, min(1.0, dot / (norm_a * norm_b)))


def _detect_boundaries(
    sentences: list[str], embedder: BaseEmbedder, similarity_drop: float
) -> set[int]:
    """返回语义边界索引；索引 i 表示句子 i 与句子 i+1 之间需要切分。"""
    vectors = embedder.embed(sentences)
    similarities = [
        _cosine_similarity(vectors[i], vectors[i + 1])
        for i in range(len(sentences) - 1)
    ]
    boundaries: set[int] = set()
    for i in range(1, len(similarities)):
        if similarities[i] < similarities[i - 1] - similarity_drop:
            boundaries.add(i)
    return boundaries


def _group_sentences(
    sentences: list[str],
    boundaries: set[int],
    chunk_size: int,
    min_chunk_size: int = 200
) -> list[str]:
    """按语义边界组装 chunk。"""
    if chunk_size < min_chunk_size + 50:
            raise ValueError("chunk_size 必须比 min_chunk_size 大50")
    chunks: list[str] = []
    current = ""
    for index, sentence in enumerate(sentences):
        if len(sentence) > chunk_size:
            # 如果有神人文档一句话就超过了文档块的最大字符数，那直接按照最大字符数硬切
            if current:
                chunks.append(current.strip())
                current = ""
            for i in range(0, len(sentence), chunk_size):
                sub = sentence[i:i+chunk_size].strip()
                if sub:
                    chunks.append(sub)
            continue

        candidate = f"{current} {sentence}" if current else sentence
        if current and len(candidate) > chunk_size:
            if len(current) >= min_chunk_size:
                # 如果加了新句子后超出最大分块大小，那将新句子推到下一个分块中
                chunks.append(current.strip())
                current = sentence
            else:
                # 如果当前分块不要新句子后，又太短，那还是要新句子吧
                current = candidate
        else:
            current = candidate

        if current and index in boundaries and len(current) >= min_chunk_size:
            # 要求 chunk_size 必须大于最低设定值，防止遇到大量散字符，chunk 过小
            chunks.append(current.strip())
            current = ""
    if current.strip():
        chunks.append(current.strip())
    return [chunk for chunk in chunks if chunk]


def split_text(
    text: str,
    chunk_size: int = 600,
    embedder: BaseEmbedder | None = None,
    similarity_drop: float = 0.15,
) -> list[str]:
    """语义分块：分句 + 相邻句子相似度突降切分（需达到最低长度）+ 最大长度兜底。

    未提供 embedder 时退化为仅按 chunk_size 按句子切分；
    语义边界计算失败时同样回退，保证文章仍可入库。
    """
    if chunk_size <= 0:
        raise ValueError("chunk_size 必须为正数")
    if similarity_drop < 0:
        raise ValueError("similarity_drop 不能为负数")

    sentences = _split_sentences(text)
    if not sentences:
        return []

    boundaries: set[int] = set()
    if embedder is not None:
        try:
            boundaries = _detect_boundaries(sentences, embedder, similarity_drop)
        except Exception:  # noqa: BLE001
            logger.warning("语义边界计算失败，回退为仅按 chunk_size 切分", exc_info=True)

    return _group_sentences(sentences, boundaries, chunk_size)
