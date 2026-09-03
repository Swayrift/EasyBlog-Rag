"""Markdown 结构化切块。

切块只依据 Markdown 结构和长度规则，不调用 Embedding 计算语义边界。
代码块、表格、列表和引用会作为结构块保留；只有超过硬上限时才按行拆分。
"""

from __future__ import annotations

import logging
import re

logger = logging.getLogger(__name__)

_FENCE_RE = re.compile(r"^\s*(`{3,}|~{3,})(.*)$")
_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+.+?\s*#*\s*$")


def _parse_blocks(text: str) -> list[str]:
    """按空行和围栏代码块解析 Markdown 结构块。"""
    lines = text.replace("\r\n", "\n").replace("\r", "\n").split("\n")
    blocks: list[str] = []
    current: list[str] = []
    fence_char: str | None = None
    fence_len = 0

    def flush() -> None:
        if current:
            block = "\n".join(current).strip()
            if block:
                blocks.append(block)
            current.clear()

    for line in lines:
        fence = _FENCE_RE.match(line)
        if fence_char is None:
            if fence:
                fence_char = fence.group(1)[0]
                fence_len = len(fence.group(1))
            elif not line.strip():
                flush()
                continue
            current.append(line)
            continue

        current.append(line)
        marker = line.lstrip()
        if marker.startswith(fence_char * fence_len) and not marker.startswith(
            fence_char * (fence_len + 1)
        ):
            fence_char = None
            fence_len = 0
            flush()

    flush()
    return blocks


def _join_headings(blocks: list[str]) -> list[str]:
    """将单独的标题和其后的内容合并，避免标题脱离正文。"""
    result: list[str] = []
    index = 0
    while index < len(blocks):
        block = blocks[index]
        if _HEADING_RE.fullmatch(block) and index + 1 < len(blocks):
            result.append(f"{block}\n\n{blocks[index + 1]}")
            index += 2
        else:
            result.append(block)
            index += 1
    return result


def _split_oversized_block(block: str, hard_max_len: int) -> list[str]:
    """拆分超长块，代码块拆分后仍保持成对围栏。"""
    if len(block) <= hard_max_len:
        return [block]

    lines = block.splitlines()
    fence = _FENCE_RE.match(lines[0]) if lines else None
    is_fenced = bool(
        fence
        and len(lines) >= 2
        and lines[-1].lstrip().startswith(fence.group(1)[0] * len(fence.group(1)))
    )
    if is_fenced:
        opening = lines[0]
        closing = lines[-1]
        body_lines = lines[1:-1]
        available = max(1, hard_max_len - len(opening) - len(closing) - 2)
        parts: list[str] = []
        current: list[str] = []
        current_len = 0
        for line in body_lines:
            if len(line) > available:
                if current:
                    parts.append("\n".join([opening, *current, closing]))
                    current = []
                    current_len = 0
                parts.extend(
                    "\n".join([opening, line[i : i + available], closing])
                    for i in range(0, len(line), available)
                )
                continue
            extra = len(line) + (1 if current else 0)
            if current and current_len + extra > available:
                parts.append("\n".join([opening, *current, closing]))
                current = []
                current_len = 0
            current.append(line)
            current_len += extra
        if current or not parts:
            parts.append("\n".join([opening, *current, closing]))
        return parts

    parts: list[str] = []
    current = []
    current_len = 0
    for line in lines:
        if len(line) > hard_max_len:
            if current:
                parts.append("\n".join(current))
                current = []
                current_len = 0
            parts.extend(
                line[i : i + hard_max_len] for i in range(0, len(line), hard_max_len)
            )
            continue
        extra = len(line) + (1 if current else 0)
        if current and current_len + extra > hard_max_len:
            parts.append("\n".join(current))
            current = []
            current_len = 0
        current.append(line)
        current_len += extra
    if current:
        parts.append("\n".join(current))
    return [part.strip() for part in parts if part.strip()]


def split_text(
    text: str,
    chunk_size: int = 600,
    min_chunk_size: int = 200,
    hard_chunk_size: int | None = None,
) -> list[str]:
    """按 Markdown 结构切分正文，不使用 Embedding 计算边界。"""
    if chunk_size <= 0:
        raise ValueError("chunk_size 必须为正数")
    if min_chunk_size < 0:
        raise ValueError("min_chunk_size 不能为负数")

    hard_max_len = hard_chunk_size or max(chunk_size * 2, chunk_size)
    if hard_max_len < chunk_size:
        raise ValueError("hard_chunk_size 不能小于 chunk_size")
    if min_chunk_size > hard_max_len:
        raise ValueError("min_chunk_size 不能大于 hard_chunk_size")
    if not text.strip():
        return []

    blocks = _join_headings(_parse_blocks(text))
    safe_blocks = [
        part for block in blocks for part in _split_oversized_block(block, hard_max_len)
    ]

    chunks: list[str] = []
    current = ""
    for block in safe_blocks:
        candidate = f"{current}\n\n{block}" if current else block
        if not current or len(candidate) <= chunk_size:
            current = candidate
        elif len(current) < min_chunk_size and len(candidate) <= hard_max_len:
            current = candidate
        else:
            chunks.append(current.strip())
            current = block
    if current.strip():
        chunks.append(current.strip())

    result = [chunk for chunk in chunks if chunk]
    logger.debug(
        "Markdown 结构化切块完成：输入 %d 字符，输出 %d 个 chunk",
        len(text),
        len(result),
    )
    return result
