"""API 请求/响应模型（Pydantic）。"""

from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field


class TagOut(BaseModel):
    id: int
    name: str
    slug: str
    post_count: int = 0


class PostListItem(BaseModel):
    id: int
    slug: str
    title: str
    summary: str
    tags: list[str] = []
    created_at: datetime
    updated_at: datetime


class PostListResponse(BaseModel):
    total: int
    page: int
    page_size: int
    items: list[PostListItem]


class PostDetail(BaseModel):
    id: int
    slug: str
    title: str
    summary: str
    content_md: str
    tags: list[str] = []
    created_at: datetime
    updated_at: datetime


class AboutResponse(BaseModel):
    name: str = ""
    summary: str = ""
    tech_stack: list[str] = []
    contact: dict[str, str] = {}
    content_md: str = ""


class ChatMessage(BaseModel):
    role: Literal["system", "user", "assistant"]
    content: str = Field(min_length=1, max_length=8000)


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=50)


class ChatSource(BaseModel):
    title: str
    source_type: str
    source_id: int
    chunk: str
    score: float


class ChatResponse(BaseModel):
    answer: str
    sources: list[ChatSource] = []


class HealthResponse(BaseModel):
    status: str
    title: str
    vector_store_ok: bool
    llm_ok: bool
    time: datetime
