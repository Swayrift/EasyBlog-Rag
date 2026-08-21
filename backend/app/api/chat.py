"""RAG 知识库问答接口。"""

from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException

from app.api.deps import get_context
from app.core.app_context import AppContext
from app.schemas.api_schemas import ChatRequest, ChatResponse, ChatSource

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
def chat(payload: ChatRequest, ctx: AppContext = Depends(get_context)) -> ChatResponse:
    messages = [message.model_dump() for message in payload.messages]
    try:
        result = ctx.rag.chat(messages)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except Exception:  # noqa: BLE001
        logger.exception("问答处理失败")
        raise HTTPException(status_code=500, detail="问答服务暂时不可用")
    return ChatResponse(
        answer=result.answer,
        sources=[
            ChatSource(
                title=source.title,
                source_type=source.source_type,
                source_id=source.source_id,
                chunk=source.chunk,
                score=source.score,
            )
            for source in result.sources
        ],
    )
