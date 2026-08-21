"""关于我接口：从 content/about.md 读取。"""

from __future__ import annotations

import logging

import yaml
from fastapi import APIRouter, Depends

from app.api.deps import get_context
from app.core.app_context import AppContext
from app.schemas.api_schemas import AboutResponse
from app.services.markdown_parser import parse_markdown

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/about", tags=["about"])


@router.get("", response_model=AboutResponse)
def about(ctx: AppContext = Depends(get_context)) -> AboutResponse:
    path = ctx.settings.about_file
    if not path.exists():
        return AboutResponse()
    parsed = parse_markdown(path.read_text(encoding="utf-8"))
    meta = parsed.meta
    tech_stack = meta.get("tech_stack") or []
    if isinstance(tech_stack, str):
        tech_stack = [tech_stack]
    contact = meta.get("contact") or {}
    if isinstance(contact, str):
        try:
            contact = yaml.safe_load(contact) or {}
        except yaml.YAMLError:
            contact = {}
    return AboutResponse(
        name=str(meta.get("name") or ""),
        summary=str(meta.get("summary") or ""),
        tech_stack=[str(item) for item in tech_stack],
        contact={str(k): str(v) for k, v in contact.items()} if isinstance(contact, dict) else {},
        content_md=parsed.body,
    )
