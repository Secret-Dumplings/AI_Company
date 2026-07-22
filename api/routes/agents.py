"""
GET /agents —— 列出所有已注册的 Agent
GET /agents/{name_or_uuid} —— 取单个 Agent 的元信息
POST /agents/{name_or_uuid}/chat —— 与 Agent 对话（流式 SSE / 非流式）
POST /agents/{name_or_uuid}/reload —— 重新加载 Agent
POST /agents —— 运行时注册 Agent
GET /agents/{name_or_uuid}/tools —— 列出该 Agent 可用的工具
"""

from __future__ import annotations

import json
import uuid as _uuid
from typing import Any, List, Optional

import dumplingsAI
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from ..deps import (
    get_agent_info,
    get_agent_list,
    get_agent_or_404,
    stream_agent_chat,
)
from ..models import (
    AgentAvailableToolsResponse,
    AgentInfo,
    AgentListResponse,
    AgentRegistrationRequest,
    AgentRegistrationResponse,
    ChatChoice,
    ChatMessage,
    ChatRequest,
    ChatResponse,
    ChatUsage,
)

router = APIRouter(prefix="/agents", tags=["agents"])


@router.get("", response_model=AgentListResponse)
async def list_agents(agent_list=Depends(get_agent_list)) -> AgentListResponse:
    """
    列出所有已注册的 Agent。

    Agent 注册时同时登记到 uuid 和 name 两个 key，所以同一个实例会出现两次。
    这里按 uuid 去重后返回。
    """
    seen = set()
    items: List[AgentInfo] = []
    for key, inst in agent_list.items():
        uuid = getattr(inst, "uuid", None)
        if uuid and uuid not in seen:
            seen.add(uuid)
            items.append(get_agent_info(inst))

    return AgentListResponse(agents=items, total=len(items))


@router.get("/{name_or_uuid}", response_model=AgentInfo)
async def get_agent(name_or_uuid: str) -> AgentInfo:
    inst = get_agent_or_404(name_or_uuid)
    return get_agent_info(inst)


@router.get("/{name_or_uuid}/tools", response_model=AgentAvailableToolsResponse)
async def list_agent_tools(name_or_uuid: str) -> AgentAvailableToolsResponse:
    """列出该 Agent 可调用的工具（注册的工具 + @builtin_tool 自动收集的）"""
    inst = get_agent_or_404(name_or_uuid)

    # 1) 注册的工具
    try:
        tools_info = dumplingsAI.tool_registry.get_all_tools_info(inst.uuid) or {}
        tool_names = sorted(tools_info.keys())
    except Exception:
        tool_names = []

    # 2) 内置工具（@builtin_tool 自动收集）
    builtin_names: List[str] = []
    try:
        for s in dumplingsAI.tool_registry.collect_builtin_tools(inst):
            n = s.get("function", {}).get("name")
            if n:
                builtin_names.append(n)
    except Exception:
        pass

    all_names = sorted(set(tool_names) | set(builtin_names))
    return AgentAvailableToolsResponse(
        agent_name=inst.name,
        tool_names=tool_names,
        builtin_tool_names=builtin_names,
        total=len(all_names),
    )


@router.post("/{name_or_uuid}/chat", response_model=None)
async def chat_with_agent(name_or_uuid: str, req: ChatRequest):
    """
    与 Agent 对话。

    - ``stream=false``（默认）：返 ``ChatResponse``（OpenAI 风格）
    - ``stream=true``：返 ``text/event-stream``，每帧一个 JSON dict
      （来自 Agent.out 的 content，event 字段分类为 text / tool_call / tool_result / done / error）
    """
    if not req.messages:
        raise HTTPException(
            status_code=422,
            detail="messages 至少要有一条",
        )

    inst = get_agent_or_404(name_or_uuid)

    # 解析最后一条 user 消息
    last_user = next(
        (m for m in reversed(req.messages) if m.role == "user"),
        None,
    )
    if last_user is None:
        raise HTTPException(
            status_code=400,
            detail="messages 中至少要有一条 role=user 的消息",
        )

    if req.stream:
        # ---- 流式 SSE ----
        async def event_source():
            async for chunk in stream_agent_chat(
                inst,
                messages=last_user.content,
                images=req.images,
                tool=req.tool,
            ):
                event = chunk.get("event")
                data = chunk.get("data", {})
                # 兼容 Agent.out 的旧 content dict 格式（不是 {"event":..., "data":...}）
                # 旧格式：{"message": "xxx"} / {"tool_name": "xxx"} / {"task": True} / {"tool_result":...}
                if "event" not in chunk:
                    if "message" in chunk:
                        event = "text"
                        data = {"delta": chunk.get("message", "")}
                    elif "tool_name" in chunk and "tool_result" not in chunk:
                        event = "tool_call"
                        data = {"name": chunk["tool_name"], "input": chunk.get("tool_parameter", {})}
                    elif "tool_result" in chunk:
                        event = "tool_result"
                        data = {"name": chunk.get("tool_name"), "result": chunk["tool_result"]}
                    elif chunk.get("task"):
                        event = "done"
                        data = {"finish_reason": "stop"}
                    else:
                        event = "text"
                        data = chunk
                payload = {
                    "event": event,
                    "data": data,
                    "agent_name": inst.name,
                    "agent_uuid": inst.uuid,
                }
                yield f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"

            # 收尾：done
            yield "data: " + json.dumps({
                "event": "done",
                "data": {"finish_reason": "stop"},
                "agent_name": inst.name,
                "agent_uuid": inst.uuid,
            }, ensure_ascii=False) + "\n\n"

        return StreamingResponse(event_source(), media_type="text/event-stream")

    # ---- 非流式 ----
    try:
        text = inst.conversation_with_tool(
            messages=last_user.content,
            tool=req.tool,
            images=req.images,
        )
    except dumplingsAI.errors.APIError as e:
        raise HTTPException(status_code=502, detail=f"LLM 调用失败：{e}") from e
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e

    return ChatResponse(
        choices=[
            ChatChoice(
                index=0,
                message=ChatMessage(role="assistant", content=text or ""),
                finish_reason="stop",
            ),
        ],
        usage=ChatUsage(),
        agent_name=inst.name,
        agent_uuid=inst.uuid,
    )


@router.post("/{name_or_uuid}/reload")
async def reload_agent(name_or_uuid: str) -> dict:
    """
    调用 Agent 的 reload()，强制重建 system prompt + 工具列表。
    """
    inst = get_agent_or_404(name_or_uuid)
    try:
        inst.reload()
    except Exception as e:  # pragma: no cover
        raise HTTPException(status_code=500, detail=str(e)) from e
    return {"status": "ok", "agent": inst.name}


@router.post("", response_model=AgentRegistrationResponse)
async def register_agent_runtime(req: AgentRegistrationRequest) -> AgentRegistrationResponse:
    """
    运行时注册 Agent。

    根据 ``req.protocol`` 选 BaseAgent 或 AnthropicAgent 作为基类，
    动态构造子类并 ``@register_agent``。

    限制：
    - 动态类没有 ``__init_subclass__`` 的钩子，所以 ``@builtin_tool`` 不会自动 promote；
      仅适合"基础对话 Agent"，需要内建工具请用 agents_config.py 写静态类
    - Agent 类的 uuid/name 必须是字符串；空字符串/None 会自动生成
    """
    try:
        if req.protocol == "anthropic":
            from dumplingsAI.anthropic_agent import AnthropicAgent
            base_cls = AnthropicAgent
        else:
            base_cls = dumplingsAI.BaseAgent

        # 动态构造子类
        uid = req.uuid or _uuid.uuid4().hex
        attrs = {
            "prompt": req.prompt,
            "fc_model": req.fc_model,
        }
        if req.api_provider is not None:
            attrs["api_provider"] = req.api_provider
        if req.model_name is not None:
            attrs["model_name"] = req.model_name
        if req.api_key is not None:
            attrs["api_key"] = req.api_key

        new_cls = type(
            f"RuntimeAgent_{req.name}",
            (base_cls,),
            attrs,
        )

        # 用 dumplingsAI.register_agent 装饰
        decorated = dumplingsAI.register_agent(uid, req.name, req.description)(new_cls)
        return AgentRegistrationResponse(
            name=req.name,
            uuid=uid,
            protocol=req.protocol,
            status="registered",
            message=f"Agent 已注册到 dumplingsAI.agent_list（key: {uid!r} / {req.name!r}）",
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e)) from e