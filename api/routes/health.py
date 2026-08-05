"""
GET /health —— 健康检查 + 当前已注册的 Agent / 工具数量
"""

from __future__ import annotations

import tangyuanAI
from fastapi import APIRouter, Depends

from ..deps import get_tool_registry
from ..models import HealthResponse

router = APIRouter(tags=["meta"])


@router.get("/health", response_model=HealthResponse)
async def health(tool_registry=Depends(get_tool_registry)) -> HealthResponse:
    try:
        tools = tool_registry.list_tools() or []
        n_tools = len(tools)
    except Exception:
        n_tools = 0

    return HealthResponse(
        status="ok",
        version=tangyuanAI.__version__,
        n_agents=len(tangyuanAI.agent_list),
        n_tools=n_tools,
    )