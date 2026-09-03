"""SQLite 表模型（SQLModel）。

对应设计稿 §8.1。posts 表在设计稿基础上增加了 file_path 字段，
用于启动时的增量同步与磁盘文件删除检测（设计稿已同步更新）。

注意：本文件不能使用 `from __future__ import annotations`，
否则 SQLAlchemy 无法解析 Relationship 的 `List["Tag"]` 等注解。
"""

from datetime import datetime
from typing import List, Optional

from sqlalchemy import Column, Integer
from sqlmodel import Field, Relationship, SQLModel


class PostTag(SQLModel, table=True):
    """文章-标签关联表。"""

    __tablename__ = "post_tags"

    post_id: Optional[int] = Field(default=None, foreign_key="posts.id", primary_key=True)
    tag_id: Optional[int] = Field(default=None, foreign_key="tags.id", primary_key=True)


class Post(SQLModel, table=True):
    __tablename__ = "posts"

    id: Optional[int] = Field(default=None, primary_key=True)
    slug: str = Field(index=True, unique=True)
    title: str
    summary: str = ""
    content_md: str = ""
    status: str = Field(default="published", index=True)  # published / draft
    file_path: str = Field(default="", index=True)  # 相对 content/ 的源文件路径
    file_hash: str = Field(default="")  # 源文件内容的 SHA-256 哈希
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    tags: List["Tag"] = Relationship(back_populates="posts", link_model=PostTag)


class Tag(SQLModel, table=True):
    __tablename__ = "tags"

    id: Optional[int] = Field(default=None, primary_key=True)
    name: str = Field(unique=True)
    slug: str = Field(unique=True)

    posts: List[Post] = Relationship(back_populates="tags", link_model=PostTag)


class Document(SQLModel, table=True):
    __tablename__ = "documents"

    id: Optional[int] = Field(default=None, primary_key=True)
    file_name: str
    title: str = ""
    file_path: str = Field(index=True, unique=True)
    file_hash: str = ""
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)


class Chunk(SQLModel, table=True):
    __tablename__ = "chunks"

    # AUTOINCREMENT 避免主键复用导致与 FAISS 向量主键错位
    id: Optional[int] = Field(
        default=None,
        sa_column=Column(Integer, primary_key=True, autoincrement=True),
    )
    source_type: str = Field(index=True)  # post / document
    source_id: int = Field(index=True)
    chunk_index: int = 0
    content: str = ""


class QaCache(SQLModel, table=True):
    """问答缓存：仅由 RAG 生成、固定有效期，缓存「问题 + 答案 + 引用来源」。"""

    __tablename__ = "qa_cache"

    id: Optional[int] = Field(default=None, primary_key=True)
    question: str
    answer: str = ""
    sources: str = "[]"  # JSON 数组，结构与 /api/chat 响应 sources 一致
    question_vector: str = "[]"  # JSON 数组（1024 维），启动时载入内存用于相似度匹配
    # status: str = Field(default="active", index=True)  # active / invalidated
    expires_at: datetime = Field(default_factory=datetime.now)
    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)
