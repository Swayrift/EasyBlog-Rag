"""标签列表接口。"""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlmodel import Session, select

from app.api.deps import get_context
from app.core.app_context import AppContext
from app.models.db_models import Post, PostTag, Tag
from app.schemas.api_schemas import TagOut

router = APIRouter(prefix="/api/tags", tags=["tags"])


@router.get("", response_model=list[TagOut])
def list_tags(ctx: AppContext = Depends(get_context)) -> list[TagOut]:
    with Session(ctx.engine) as session:
        rows = session.exec(
            select(Tag, func.count(PostTag.post_id))
            .join(PostTag, PostTag.tag_id == Tag.id, isouter=True)
            .join(Post, Post.id == PostTag.post_id, isouter=True)
            .group_by(Tag.id)
        ).all()
        result = []
        for tag, count in rows:
            # 仅统计已发布文章
            published = session.exec(
                select(func.count(PostTag.post_id))
                .join(Post, Post.id == PostTag.post_id)
                .where(PostTag.tag_id == tag.id, Post.status == "published")
            ).one()
            result.append(TagOut(id=tag.id, name=tag.name, slug=tag.slug, post_count=published))
        return result
