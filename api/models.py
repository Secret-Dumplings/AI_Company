"""
Pydantic 模型：HTTP 请求 / 响应。

设计目标：
- 请求 / 响应尽量对齐 OpenAI Chat Completions API 风格，让现有客户端零改动接入
- 但增加 ``agent_name`` 等扩展字段，让 ai-company 特有的"多 Agent"功能可用
"""

from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# /health
# ---------------------------------------------------------------------------

class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    version: str
    n_agents: int
    n_tools: int


# ---------------------------------------------------------------------------
# /agents
# ---------------------------------------------------------------------------

class AgentInfo(BaseModel):
    """单个 Agent 的元信息"""
    name: str
    uuid: str
    description: Optional[str] = None
    protocol: Optional[str] = None            # "openai" / "anthropic" / None (基类)
    api_provider: Optional[str] = None
    model_name: Optional[str] = None
    fc_model: bool = False


class AgentListResponse(BaseModel):
    agents: List[AgentInfo]
    total: int


# ---------------------------------------------------------------------------
# /agents/{name}/chat —— OpenAI 兼容风格 + ai-company 扩展
# ---------------------------------------------------------------------------

class ChatMessage(BaseModel):
    """OpenAI 风格的单条消息"""
    role: Literal["system", "user", "assistant", "tool"]
    content: str
    name: Optional[str] = None               # 工具名（role=tool 时）


class ImageURL(BaseModel):
    """OpenAI vision 风格的图片 URL（仅当 role=user 时支持）"""
    url: str
    detail: Optional[Literal["auto", "low", "high"]] = None


class ChatRequest(BaseModel):
    """
    OpenAI 风格的 chat 请求 + ai-company 扩展。

    必填：
        messages           对话历史（可包含 system / user / assistant / tool）

    可选（OpenAI 兼容）：
        stream             是否流式（SSE，默认 false）
        temperature        当前框架未使用，预留
        max_tokens         当前框架未使用，预留

    可选（ai-company 扩展）：
        images             多模态图片 URL 列表（仅最后一条 user 消息生效）
        tool               True 表示由 ask_for_help 内部递归调用，不要再加 user 消息
        extra_kwargs       透传给 conversation_with_tool 的额外参数
    """
    messages: List[ChatMessage] = Field(..., min_length=1)

    # OpenAI 风格可选字段
    stream: bool = False
    temperature: Optional[float] = None
    max_tokens: Optional[int] = None

    # ai-company 扩展
    images: Optional[List[str]] = None
    tool: bool = False
    extra_kwargs: Optional[Dict[str, Any]] = None


class ChatChoice(BaseModel):
    index: int = 0
    message: ChatMessage
    finish_reason: str = "stop"


class ChatUsage(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0


class ChatResponse(BaseModel):
    """
    OpenAI 风格的 chat 响应。
    """
    id: str = Field(default_factory=lambda: f"chatcmpl-{id(object())}")
    object: Literal["chat.completion"] = "chat.completion"
    created: int = Field(default_factory=lambda: __import__('time').time())
    model: str = "dumplingsAI"
    choices: List[ChatChoice]
    usage: ChatUsage = Field(default_factory=ChatUsage)
    agent_name: str
    agent_uuid: str


# ---------------------------------------------------------------------------
# 流式 SSE：每帧一个 dict（与 Agent.out 内部 content 字段对齐）
# ---------------------------------------------------------------------------

class StreamChunk(BaseModel):
    """SSE 一帧内容"""
    event: Literal[
        "text",       # 文本增量
        "tool_call",  # 工具调用
        "tool_result",  # 工具返回
        "done",       # 收尾
        "error",      # 错误
    ]
    data: Dict[str, Any] = Field(default_factory=dict)
    agent_name: Optional[str] = None
    agent_uuid: Optional[str] = None


# ---------------------------------------------------------------------------
# /tools —— 注册
# ---------------------------------------------------------------------------

class ToolRegistrationRequest(BaseModel):
    """运行时注册工具的请求

    注意：当前 dumplingsAI.tool_registry 没有真正支持"运行时注册已存在的函数"，
    所以这个 endpoint 只能让 server 端 import 一个函数引用（通过 module:function 路径）。
    实际落地用得最多的场景是"启动期注册"（通过 agents_config.py 一次到位），
    这里保留接口以备后续扩展。
    """
    name: str
    description: str = ""
    parameters: Dict[str, Any] = Field(default_factory=dict)
    allowed_agents: Optional[List[str]] = None  # None 表示全局可用
    module_path: Optional[str] = None            # "package.module:function_name"
    note: Optional[str] = None


class ToolRegistrationResponse(BaseModel):
    name: str
    status: Literal["registered", "error"]
    message: str


class AgentAvailableToolsResponse(BaseModel):
    """GET /agents/{name}/tools —— 该 Agent 可调用的工具列表"""
    agent_name: str
    tool_names: List[str]
    builtin_tool_names: List[str] = Field(default_factory=list)
    total: int


# ---------------------------------------------------------------------------
# /agents —— 运行时注册
# ---------------------------------------------------------------------------

class AgentRegistrationRequest(BaseModel):
    """
    运行时注册 Agent。

    接收最小化的必填字段，自动构造一个 dumplingsAI.Agent 子类并 register。
    缺点：动态类没有 __init_subclass__ 的钩子（子类覆写 @builtin_tool 时不会自动 promote），
    所以仅适合"基础对话场景"，需要 builtin_tool 的话还是用 agents_config.py 写静态类。
    """
    uuid: Optional[str] = None
    name: str
    description: Optional[str] = None
    protocol: Literal["openai", "anthropic"] = "openai"
    prompt: str = "你是一个助手"
    api_provider: Optional[str] = None
    model_name: Optional[str] = None
    api_key: Optional[str] = None
    fc_model: bool = True


class AgentRegistrationResponse(BaseModel):
    name: str
    uuid: str
    protocol: str
    status: Literal["registered", "error"]
    message: str


# ---------------------------------------------------------------------------
# /skills
# ---------------------------------------------------------------------------

class SkillInfo(BaseModel):
    name: str
    description: Optional[str] = None
    path: Optional[str] = None
    tags: List[str] = Field(default_factory=list)


class SkillListResponse(BaseModel):
    skills: List[SkillInfo]
    total: int


class SkillScanRequest(BaseModel):
    """POST /skills/scan 的请求体"""
    paths: List[str]                          # 绝对路径列表


class SkillRegisterRequest(BaseModel):
    """POST /skills/register 的请求体"""
    path: str                                  # 绝对路径


# ---------------------------------------------------------------------------
# /mcp
# ---------------------------------------------------------------------------

class MCPSessionInfo(BaseModel):
    server_path: str
    n_tools: int
    n_resources: int = 0
    created_at: Optional[float] = None


class MCPSessionListResponse(BaseModel):
    sessions: List[MCPSessionInfo]
    total: int


class MCPRegisterRequest(BaseModel):
    """POST /mcp/tools 的请求体"""
    server_path: str
    register_resources: bool = True
    allowed_agents: Optional[List[str]] = None


class MCPHealthCheckRequest(BaseModel):
    interval: float = 60.0


# ---------------------------------------------------------------------------
# /tools
# ---------------------------------------------------------------------------

class ToolInfo(BaseModel):
    name: str
    description: str
    allowed_agents: Optional[List[str]] = None


class ToolListResponse(BaseModel):
    tools: List[ToolInfo]
    total: int