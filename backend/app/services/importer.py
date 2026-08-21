"""知识导入器：扫描文章与本地文档，写入 SQLite 并切分向量化入库。

- 文章（content/posts）与文档（content/documents）均以文件哈希判断是否变更。
- 已删除文件对应的记录与向量会被清理。
- 每次后端启动时自动执行，也可单独运行 scripts/sync_knowledge.py。
"""

from __future__ import annotations

import hashlib
import logging
from pathlib import Path

from sqlmodel import Session, select

from app.core.config import Settings
from app.models.db_models import Chunk, Document, Post, PostTag, Tag
from app.services.chunker import split_text
from app.services.embedding import BaseEmbedder
from app.services.markdown_parser import normalize_tags, parse_datetime, parse_markdown
from app.services.milvus_store import VectorRecord, VectorStore

logger = logging.getLogger(__name__)


def _file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _slugify(name: str) -> str:
    return name.strip().lower().replace(" ", "-") or name


def _get_or_create_tag(session: Session, name: str) -> Tag:
    tag = session.exec(select(Tag).where(Tag.name == name)).first()
    if tag is None:
        tag = Tag(name=name, slug=_slugify(name))
        session.add(tag)
        session.flush()
    return tag


def _delete_source_vectors(
    vector_store: VectorStore | None, session: Session, source_type: str, source_id: int
) -> None:
    chunks = session.exec(
        select(Chunk).where(Chunk.source_type == source_type, Chunk.source_id == source_id)
    ).all()
    if not chunks:
        return
    if vector_store is not None:
        vector_store.delete([int(chunk.milvus_id) for chunk in chunks if chunk.milvus_id])
    for chunk in chunks:
        session.delete(chunk)


def _rebuild_chunks(
    vector_store: VectorStore | None,
    embedder: BaseEmbedder | None,
    session: Session,
    source_type: str,
    source_id: int,
    title: str,
    body: str,
    settings: Settings,
) -> None:
    _delete_source_vectors(vector_store, session, source_type, source_id)

    if vector_store is None or embedder is None:
        logger.warning("%s[%s] 向量服务不可用，跳过切分与向量化", source_type, title)
        return

    texts = split_text(
        body,
        settings.chunk_size,
        embedder,
        settings.similarity_drop,
    )
    if not texts:
        return
    vectors = embedder.embed(texts)

    for index, (text, vector) in enumerate(zip(texts, vectors)):
        chunk = Chunk(source_type=source_type, source_id=source_id, chunk_index=index, content=text)
        session.add(chunk)
        session.flush()
        chunk.milvus_id = str(chunk.id)
        session.add(chunk)
        vector_store.upsert(
            [
                VectorRecord(
                    id=chunk.id,
                    embedding=vector,
                    source_type=source_type,
                    source_id=source_id,
                    title=title,
                )
            ]
        )
    logger.info("%s[%s] 切分为 %d 个片段并已向量化", source_type, title, len(texts))


def _sync_post(
    vector_store: VectorStore | None,
    embedder: BaseEmbedder | None,
    session: Session,
    path: Path,
    settings: Settings,
) -> str:
    parsed = parse_markdown(path.read_text(encoding="utf-8"))
    meta = parsed.meta
    title = str(meta.get("title") or path.stem)
    slug = str(meta.get("slug") or _slugify(path.stem))
    summary = str(meta.get("summary") or "")
    status = str(meta.get("status") or "published")
    tag_names = normalize_tags(meta.get("tags"))

    post = session.exec(select(Post).where(Post.slug == slug)).first()
    if post is None:
        post = Post(slug=slug, title=title)
        created_at = parse_datetime(meta.get("created_at")) or parse_datetime(meta.get("date"))
        if created_at is not None:
            post.created_at = created_at
        session.add(post)
        session.flush()

    body = parsed.body
    content_hash = hashlib.sha256(body.encode("utf-8")).hexdigest()
    changed = post.content_md != body or post.title != title or post.summary != summary

    post.title = title
    post.summary = summary
    post.content_md = body
    post.status = status
    post.file_path = path.relative_to(settings.posts_dir).as_posix()

    for link in session.exec(select(PostTag).where(PostTag.post_id == post.id)).all():
        session.delete(link)
    for tag_name in tag_names:
        tag = _get_or_create_tag(session, tag_name)
        session.add(PostTag(post_id=post.id, tag_id=tag.id))

    if changed or not session.exec(
        select(Chunk).where(Chunk.source_type == "post", Chunk.source_id == post.id).limit(1)
    ).first():
        _rebuild_chunks(vector_store, embedder, session, "post", post.id, post.title, body, settings)
    else:
        logger.debug("文章未变更，跳过：%s", slug)
    logger.info("同步文章：%s（%s）", title, content_hash[:8])
    return slug


def _sync_document(
    vector_store: VectorStore | None,
    embedder: BaseEmbedder | None,
    session: Session,
    path: Path,
    rel_path: str,
    settings: Settings,
) -> None:
    raw = path.read_bytes()
    file_hash = hashlib.sha256(raw).hexdigest()
    parsed = parse_markdown(raw.decode("utf-8"))
    title = str(parsed.meta.get("title") or path.stem)

    doc = session.exec(select(Document).where(Document.file_path == rel_path)).first()
    if doc is None:
        doc = Document(file_name=path.name, title=title, file_path=rel_path, file_type=path.suffix.lstrip("."))
        session.add(doc)
        session.flush()

    changed = doc.file_hash != file_hash or doc.title != title
    doc.title = title
    doc.file_hash = file_hash
    doc.status = "active"

    if changed or not session.exec(
        select(Chunk).where(Chunk.source_type == "document", Chunk.source_id == doc.id).limit(1)
    ).first():
        _rebuild_chunks(vector_store, embedder, session, "document", doc.id, doc.title, parsed.body, settings)
    else:
        logger.debug("文档未变更，跳过：%s", rel_path)
    logger.info("同步文档：%s（%s）", rel_path, file_hash[:8])


def sync_knowledge(
    settings: Settings, engine, vector_store: VectorStore | None, embedder: BaseEmbedder | None
) -> None:
    # 即使向量服务不可用，也会完成 SQLite 元数据同步，仅跳过向量化。
    with Session(engine) as session:
        # 文章
        seen_post_slugs: set[str] = set()
        if settings.posts_dir.exists():
            for path in sorted(settings.posts_dir.rglob("*.md")):
                try:
                    slug = _sync_post(vector_store, embedder, session, path, settings)
                    seen_post_slugs.add(slug)
                except Exception:  # noqa: BLE001
                    logger.exception("同步文章失败：%s", path)

        # 清理磁盘上已删除的文章
        for post in session.exec(select(Post)).all():
            if post.slug not in seen_post_slugs:
                _delete_source_vectors(vector_store, session, "post", post.id)
                for link in session.exec(select(PostTag).where(PostTag.post_id == post.id)).all():
                    session.delete(link)
                session.delete(post)
                logger.info("文章已删除，清理：%s", post.slug)

        # 本地文档
        seen_doc_paths: set[str] = set()
        if settings.documents_dir.exists():
            for path in sorted(settings.documents_dir.rglob("*.md")):
                rel_path = path.relative_to(settings.documents_dir).as_posix()
                try:
                    _sync_document(vector_store, embedder, session, path, rel_path, settings)
                    seen_doc_paths.add(rel_path)
                except Exception:  # noqa: BLE001
                    logger.exception("同步文档失败：%s", path)

        # 清理已删除的文档记录与向量
        for doc in session.exec(select(Document).where(Document.status == "active")).all():
            if doc.file_path not in seen_doc_paths:
                _delete_source_vectors(vector_store, session, "document", doc.id)
                doc.status = "removed"
                session.add(doc)
                logger.info("文档已删除，清理：%s", doc.file_path)

        session.commit()
    logger.info("知识同步完成")
