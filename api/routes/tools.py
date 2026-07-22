"""
GET /tools —— 列出所有已注册的工具
POST /tools —— 运行时注册工具（通过 module:function 路径）
"""

from __future__ import annotations

import importlib
from typing import Any, List

from fastapi import APIRouter, Depends, HTTPException

from ..deps import get_tool_registry
from ..models import (
    ToolInfo,
    ToolListResponse,
    ToolRegistrationRequest,
    ToolRegistrationResponse,
)

router = APIRouter(prefix="/tools", tags=["tools"])


@router.get("", response_model=ToolListResponse)
async def list_tools(registry: Any = Depends(get_tool_registry)) -> ToolListResponse:
    """
    列出全部工具。``description`` 来自工具注册时提供的元数据；
    ``allowed_agents`` 暂时为 None（ACL 信息需要 tool_registry 暴露更多接口）。
    """
    raw = registry.list_tools() or []
    info = {}
    try:
        info = registry.get_all_tools_info() or {}
    except Exception:
        pass

    items: List[ToolInfo] = []
    for name in raw:
        meta = info.get(name, {})
        items.append(
            ToolInfo(
                name=name,
                description=meta.get("description", "") if isinstance(meta, dict) else "",
                allowed_agents=None,  # 留给后续版本
            )
        )
    return ToolListResponse(tools=items, total=len(items))


@router.post("", response_model=ToolRegistrationResponse)
async def register_tool_runtime(req: ToolRegistrationRequest, registry: Any = Depends(get_tool_registry)) -> ToolRegistrationResponse:
    """
    运行时注册工具。

    通过 ``module_path``（形如 ``package.module:function_name``）导入函数引用，
    然后用 ``tool_registry.register_tool`` 装饰器重新注册。

    注意：
    - 这等价于在 agents_config.py 里写 @register_tool(...)，只是入口从文件搬到 HTTP
    - 函数引用必须能被 import；本地脚本里的 lambda / 内嵌函数无法用这种方式注册
    """
    if not req.module_path:
        raise HTTPException(
            status_code=400,
            detail="runtime 注册工具必须提供 module_path（如 'examples.api.agents_config:echo'）",
        )
    try:
        module_name, func_name = req.module_path.split(":", 1)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"module_path 格式错误：{req.module_path!r}（应是 'module:function'）",
        )

    try:
        module = importlib.import_module(module_name)
        func = getattr(module, func_name)
    except (ImportError, AttributeError) as e:
        raise HTTPException(
            status_code=404,
            detail=f"找不到函数 {module_name}.{func_name}：{e}",
        )

    try:
        decorated = registry.register_tool(
            allowed_agents=req.allowed_agents,
            name=req.name,
            description=req.description,
            parameters=req.parameters,
        )(func)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"register_tool 失败：{e}") from e

    return ToolRegistrationResponse(
        name=req.name,
        status="registered",
        message=f"工具 {req.name!r} 已注册（key={req.name!r}）" + (f"。备注：{req.note}" if req.note else ""),
    )