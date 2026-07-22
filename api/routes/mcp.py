"""
POST /mcp/tools —— 注册 MCP 服务器的所有工具
GET /mcp/sessions —— 列出所有 MCP 会话
GET /mcp/sessions/{server_path} —— 单个会话详情
DELETE /mcp/sessions —— 关闭所有 MCP 会话
DELETE /mcp/sessions/{server_path} —— 关闭单个 MCP 会话
POST /mcp/health-check/start —— 启动会话池健康检查
POST /mcp/health-check/stop —— 停止会话池健康检查
"""

from __future__ import annotations

from typing import List

import dumplingsAI
from fastapi import APIRouter, HTTPException

from ..models import (
    MCPHealthCheckRequest,
    MCPRegisterRequest,
    MCPSessionInfo,
    MCPSessionListResponse,
)

router = APIRouter(prefix="/mcp", tags=["mcp"])


@router.post("/tools", response_model=dict)
async def register_mcp(req: MCPRegisterRequest) -> dict:
    """注册一个 MCP 服务器（拉起 stdio 进程，把它的所有工具 + 资源注册为标准 tool）"""
    try:
        dumplingsAI.register_mcp_tools(
            server_path=req.server_path,
            register_resources=req.register_resources,
            allowed_agents=req.allowed_agents,
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"注册 MCP 失败：{e}") from e
    return {"status": "ok", "server_path": req.server_path}


@router.get("/sessions", response_model=MCPSessionListResponse)
async def list_sessions() -> MCPSessionListResponse:
    """列出全部 MCP 会话及其工具数"""
    raw = dumplingsAI.get_session_info() or {}
    items: List[MCPSessionInfo] = []
    for path, info in raw.items():
        items.append(
            MCPSessionInfo(
                server_path=path,
                n_tools=info.get("tools_count", 0),
                n_resources=info.get("resources_count", 0),
                created_at=info.get("last_used"),
            )
        )
    return MCPSessionListResponse(sessions=items, total=len(items))


@router.get("/sessions/{server_path}")
async def get_session(server_path: str) -> dict:
    """单个会话的详情（含 tools / resources 名称列表）"""
    info = dumplingsAI.get_session_info(server_path)
    if not info:
        raise HTTPException(status_code=404, detail=f"MCP 会话不存在：{server_path!r}")
    return {"server_path": server_path, **info}


@router.delete("/sessions")
async def close_all_sessions() -> dict:
    """关闭所有 MCP 会话。

    mcp_bridge.py 的 sync 包装函数用 ``asyncio.run()`` 关闭；
    当我们在 FastAPI async 路由里调它时已经有 event loop 在跑，会抛
    ``RuntimeError: ... cannot be called from a running event loop``。
    这里做兼容：优先用 sync 版（在外部进程如 CLI 跑），fallback 到 async 版。
    """
    try:
        n = dumplingsAI.close_all_mcp_sessions_sync()
    except RuntimeError as e:
        msg = str(e)
        if "running" not in msg:
            raise
        from dumplingsAI.mcp_bridge import close_all_mcp_sessions as _async
        n = await _async()
    return {"status": "ok", "closed": n}


@router.delete("/sessions/{server_path}")
async def close_session(server_path: str) -> dict:
    """关闭单个 MCP 会话"""
    ok = dumplingsAI.close_mcp_session_sync(server_path)
    return {"status": "ok" if ok else "not_found", "server_path": server_path}


@router.post("/health-check/start")
async def start_health_check(req: MCPHealthCheckRequest) -> dict:
    """启动会话池健康检查（异步任务，interval 秒检查一次空闲会话）。

    与 close_all 同理：sync 版用 asyncio.run()，在 FastAPI async 里会崩；
    这里直接走 sync 包装内部做的 asyncio.run() 不行，所以调底层的
    _global_session_pool.start_health_check 需要已经存在的 event loop。
    """
    try:
        dumplingsAI.start_health_check(interval=req.interval)
    except RuntimeError as e:
        msg = str(e)
        if "running" not in msg and "already running" not in msg:
            raise
        import asyncio as _asyncio
        from dumplingsAI.mcp_bridge import _global_session_pool
        _asyncio.create_task(_global_session_pool.start_health_check(req.interval))
    return {"status": "ok", "interval": req.interval}


@router.post("/health-check/stop")
async def stop_health_check() -> dict:
    """停止会话池健康检查"""
    try:
        dumplingsAI.stop_health_check()
    except RuntimeError as e:
        msg = str(e)
        if "running" not in msg and "already running" not in msg:
            raise
        import asyncio as _asyncio
        from dumplingsAI.mcp_bridge import _global_session_pool
        _asyncio.create_task(_global_session_pool.stop_health_check())
    return {"status": "ok"}