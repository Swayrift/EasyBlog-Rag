"""路由依赖：从 app.state 获取共享服务。"""

from __future__ import annotations

from fastapi import Request

from app.core.app_context import AppContext


def get_context(request: Request) -> AppContext:
    return request.app.state.ctx
