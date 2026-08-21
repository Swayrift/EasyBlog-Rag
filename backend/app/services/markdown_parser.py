"""Markdown 解析：front matter + 正文。"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date, datetime

import yaml

_FRONT_MATTER_RE = re.compile(r"\A\ufeff?---[ \t]*\n(.*?)\n---[ \t]*\n?", re.DOTALL)


@dataclass
class ParsedMarkdown:
    meta: dict = field(default_factory=dict)
    body: str = ""


def parse_markdown(text: str) -> ParsedMarkdown:
    match = _FRONT_MATTER_RE.match(text)
    if not match:
        return ParsedMarkdown(body=text.strip())
    try:
        meta = yaml.safe_load(match.group(1))
    except yaml.YAMLError:
        meta = {}
    if not isinstance(meta, dict):
        meta = {}
    return ParsedMarkdown(meta=meta, body=text[match.end() :].strip())


def parse_datetime(value) -> datetime | None:
    if isinstance(value, datetime):
        return value
    if isinstance(value, date):
        return datetime(value.year, value.month, value.day)
    if isinstance(value, str):
        for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%d %H:%M", "%Y-%m-%d"):
            try:
                return datetime.strptime(value.strip(), fmt)
            except ValueError:
                continue
    return None


def normalize_tags(value) -> list[str]:
    """front matter 中 tags 支持列表或逗号分隔字符串。"""
    if value is None:
        return []
    if isinstance(value, str):
        items = re.split(r"[,，;；]", value)
    elif isinstance(value, (list, tuple)):
        items = [str(item) for item in value]
    else:
        return []
    return [item.strip() for item in items if str(item).strip()]
