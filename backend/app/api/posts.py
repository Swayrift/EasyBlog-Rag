"""文章列表与详情接口。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlmodel import Session, select

from app.api.deps import get_context
from app.core.app_context import AppContext
from app.models.db_models import Post, PostTag, Tag
from app.schemas.api_schemas import PostDetail, PostListItem, PostListResponse

router = APIRouter(prefix="/api/posts", tags=["posts"])


def _tag_names(session: Session, post_id: int) -> list[str]:
    rows = session.exec(
        select(Tag.name)
        .join(PostTag, PostTag.tag_id == Tag.id)
        .where(PostTag.post_id == post_id)
    ).all()
    return list(rows)


@router.get("", response_model=PostListResponse)
def list_posts(
    ctx: AppContext = Depends(get_context),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50),
    tag: str | None = Query(None, description="按标签名筛选"),
) -> PostListResponse:
    with Session(ctx.engine) as session:
        stmt = select(Post).where(Post.status == "published")
        if tag:
            stmt = (
                stmt.join(PostTag, PostTag.post_id == Post.id)
                .join(Tag, Tag.id == PostTag.tag_id)
                .where(Tag.name == tag)
            )
        total_posts = session.exec(stmt).all()
        total = len(total_posts)
        posts = session.exec(
            stmt.order_by(Post.created_at.desc()).offset((page - 1) * page_size).limit(page_size)
        ).all()
        items = [
            PostListItem(
                id=post.id,
                slug=post.slug,
                title=post.title,
                summary=post.summary,
                tags=_tag_names(session, post.id),
                created_at=post.created_at,
                updated_at=post.updated_at,
            )
            for post in posts
        ]
    return PostListResponse(total=total, page=page, page_size=page_size, items=items)


@router.get("/id/{post_id}", response_model=PostListItem)
def get_post_by_id(post_id: int, ctx: AppContext = Depends(get_context)) -> PostListItem:
    """按数据库主键查文章。

    供前端把问答引用来源（source_type=post, source_id）解析为可跳转的文章 slug。
    注意：本路由需声明在 "/{slug}" 之前，避免 "id" 被误当作 slug。
    """
    with Session(ctx.engine) as session:
        post = session.exec(
            select(Post).where(Post.id == post_id, Post.status == "published")
        ).first()
        if post is None:
            raise HTTPException(status_code=404, detail="文章不存在")
        return PostListItem(
            id=post.id,
            slug=post.slug,
            title=post.title,
            summary=post.summary,
            tags=_tag_names(session, post.id),
            created_at=post.created_at,
            updated_at=post.updated_at,
        )


@router.get("/{slug}", response_model=PostDetail)
def get_post(slug: str, ctx: AppContext = Depends(get_context)) -> PostDetail:
    with Session(ctx.engine) as session:
        post = session.exec(
            select(Post).where(Post.slug == slug, Post.status == "published")
        ).first()
        if post is None:
            raise HTTPException(status_code=404, detail="文章不存在")
        return PostDetail(
            id=post.id,
            slug=post.slug,
            title=post.title,
            summary=post.summary,
            content_md=post.content_md,
            tags=_tag_names(session, post.id),
            created_at=post.created_at,
            updated_at=post.updated_at,
        )
