"""
FastAPI 依赖注入：把 dumplingsAI 的全局对象暴露给路由。

不在路由函数里 import dumplingsAI / agent_list / tool_registry，
而是通过 Depends 注入 —— 便于测试时替换为 mock。
"""

from __future__ import annotations

import asyncio
from typing import Any, Dict, Optional

import dumplingsAI
from fastapi import HTTPException

from .models import AgentInfo


def get_agent_list() -> Dict[str, Any]:
    """返回 dumplingsAI.agent_list 字典（key: uuid or name）"""
    return dumplingsAI.agent_list


def get_tool_registry() -> Any:
    """返回 dumplingsAI.tool_registry 实例"""
    return dumplingsAI.tool_registry


def get_agent_or_404(name_or_uuid: str) -> Any:
    """
    根据名称或 UUID 取 Agent 实例。

    Agent 注册时同时登记到两个 key（uuid 和 name），所以一次 lookup 就能命中。
    """
    inst = dumplingsAI.agent_list.get(name_or_uuid)
    if inst is None:
        raise HTTPException(
            status_code=404,
            detail=f"Agent 不存在：{name_or_uuid!r}。"
                   f"已注册：{sorted(dumplingsAI.agent_list.keys())}",
        )
    return inst


def get_agent_info(inst: Any) -> AgentInfo:
    """从 Agent 实例提取元信息，返回 AgentInfo"""
    cls = type(inst)
    return AgentInfo(
        name=getattr(cls, "name", None) or inst.name,
        uuid=getattr(cls, "uuid", None) or inst.uuid,
        description=getattr(inst, "description", None),
        protocol=getattr(cls, "protocol", None),
        api_provider=getattr(cls, "api_provider", None),
        model_name=getattr(cls, "model_name", None),
        fc_model=bool(getattr(cls, "fc_model", False)),
    )


# ---------------------------------------------------------------------------
# 流式对话支持：monkey-patch self.out 把事件推到 asyncio.Queue
# ---------------------------------------------------------------------------

async def stream_agent_chat(
    inst: Any,
    *,
    messages,
    images: Optional[Any] = None,
    tool: bool = False,
):
    """
    在后台线程跑 ``conversation_with_tool``，把每次 ``self.out(...)`` 的内容
    异步推到 SSE 端点。

    为什么不直接调 ``conversation_with_tool(stream=True)``？因为：

    1. Agent 的 stream 是 LLM 侧的流式，``conversation_with_tool`` 本身仍是**同步阻塞**
       函数 —— 跑完全部循环才返回，事件没法"边收边发"
    2. 真正的"流式 HTTP"需要在调用线程能持续 yield

    这里的策略：

    - 把 ``conversation_with_tool`` 丢到 ``asyncio.to_thread`` 后台跑
    - monkey-patch ``inst.out``：保留原行为 + 同时把 content 推到 asyncio.Queue
    - 线程结束后推一个 sentinel ``{"event": "done", "data": {...}, ...}``
    - async generator ``__aexit__`` 时还原 ``inst.out``，避免污染后续请求

    注意：

    - 多个并发请求会共享同一个 Agent 实例的 out；目前靠 ``asyncio.Lock`` 保证
      patch/restore 不会乱
    - 如果用户已经注册了自己的 hook（``register_tool_hook``），它们不受影响——
      我们只 patch ``out``，hook 是另一条线
    """
    queue: asyncio.Queue = asyncio.Queue()
    original_out = inst.out
    sentinel = object()

    # 必须在 main event loop 里拿 loop handle；如果在子线程（runner / out）里
    # 调 asyncio.get_event_loop() 会创建新 loop，导致 call_soon_threadsafe
    # 推到一个**没有人 await 的** queue 上 —— 测试时表现为流式端点 hang。
    main_loop = asyncio.get_running_loop()

    def patched_out(content: dict) -> None:
        # 1) 推 queue（线程安全）—— 用 main_loop 而非 asyncio.get_event_loop()
        try:
            main_loop.call_soon_threadsafe(queue.put_nowait, content.copy())
        except RuntimeError:
            # loop 已关
            pass
        # 2) 保留原行为（默认 print / 自定义输出）
        try:
            original_out(content)
        except Exception:
            pass

    inst.out = patched_out
    final_text_holder: dict = {"text": ""}

    def runner():
        try:
            text = inst.conversation_with_tool(
                messages=messages,
                tool=tool,
                images=images,
            )
            final_text_holder["text"] = text or ""
        except Exception as e:  # pragma: no cover
            main_loop.call_soon_threadsafe(
                queue.put_nowait,
                {"event": "error", "data": {"message": str(e)}},
            )
        finally:
            main_loop.call_soon_threadsafe(queue.put_nowait, sentinel)
            main_loop.call_soon_threadsafe(queue.put_nowait, None)  # 双重保险

    asyncio.create_task(asyncio.to_thread(runner))

    try:
        while True:
            item = await queue.get()
            if item is sentinel or item is None:
                break
            yield item
    finally:
        # 还原 out
        try:
            inst.out = original_out
        except Exception:
            pass


# ---------------------------------------------------------------------------
# Token 计数：从最近的 usage 记录聚合
# ---------------------------------------------------------------------------

class _UsageAccumulator:
    """聚合 LLM 调用的 token 计数（Agent 内部 self.usage 由调用方维护）"""

    def __init__(self):
        self.prompt_tokens = 0
        self.completion_tokens = 0

    def update(self, prompt: int, completion: int) -> None:
        self.prompt_tokens += prompt or 0
        self.completion_tokens += completion or 0

    def total(self) -> int:
        return self.prompt_tokens + self.completion_tokens