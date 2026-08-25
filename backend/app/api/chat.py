"""RAG 知识库问答接口。"""

from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.api.deps import get_context
from app.core.app_context import AppContext
from app.schemas.api_schemas import ChatRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("")
def chat(payload: ChatRequest, ctx: AppContext = Depends(get_context)) -> StreamingResponse:
    messages = [message.model_dump() for message in payload.messages]
    try:
        ctx.rag.validate_messages(messages)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))

    def event_stream():
        try:
            for event in ctx.rag.chat_stream(messages):
                yield f"data: {json.dumps(event, ensure_ascii=False)}\n\n"
        except Exception:  # noqa: BLE001
            logger.exception("问答流式处理失败")
            error = {"type": "error", "message": "问答服务暂时不可用"}
            yield f"data: {json.dumps(error, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )
