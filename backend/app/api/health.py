"""健康检查接口。"""

from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends

from app.api.deps import get_context
from app.core.app_context import AppContext
from app.schemas.api_schemas import HealthResponse

router = APIRouter(tags=["health"])


@router.get("/api/health", response_model=HealthResponse)
def health(ctx: AppContext = Depends(get_context)) -> HealthResponse:
    return HealthResponse(
        status="ok",
        title=ctx.settings.title,
        vector_store_ok=ctx.vector_store is not None,
        llm_ok=ctx.llm.available,
        time=datetime.now(),
    )
