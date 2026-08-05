"""
Agent 配置示例 —— 业务方在这个文件里写 @template_agent。

启动方式::

    # 默认会加载本文件（examples/api/agents_config.py）
    uv run uvicorn api.app:app --reload

    # 或指定其他文件
    AGENTS_CONFIG=/path/to/my_agents.py uv run uvicorn api.app:app --reload

    # 跳过加载
    AGENTS_CONFIG="" uv run uvicorn api.app:app --reload

只要 import 这个文件，@template_agent 装饰器就把 Agent 类登记到
``agent_template_pool``；需要实例化时调 ``tangyuanAI.activate_template(name)``
（API 启动时 app.py 会自动激活所有已登记模板）。
"""

import os
import uuid

import tangyuanAI
from tangyuanAI.Agent_list import activate_template


# 示例 Agent 1：单 Agent 基础用法（OpenAI 协议）
@tangyuanAI.template_agent(
    "api_demo_agent",
    uuid=uuid.uuid4().hex,
    description="HTTP API 演示 Agent（OpenAI 协议）",
)
class APIDemoAgent(tangyuanAI.BaseAgent):
    """HTTP API 演示 Agent"""
    prompt = "你是一个友好的助手，用简洁的中文回答用户问题。"
    api_provider = "https://api.example.com/v1/chat/completions"
    model_name = os.getenv("OPENAI_MODEL")
    api_key = os.getenv("OPENAI_API_KEY")
    fc_model = True


# 示例 Agent 2：用统一的 Agent + protocol 字段切到 Anthropic
@tangyuanAI.template_agent(
    "api_claude_agent",
    uuid=uuid.uuid4().hex,
    description="HTTP API 演示 Agent（Anthropic 协议）",
)
class APIClaudeAgent(tangyuanAI.Agent):
    """HTTP API 演示 Agent（Anthropic 协议）"""
    protocol = "anthropic"
    prompt = "你是一个友好的助手，用简洁的中文回答用户问题。"
    model_name = os.getenv("ANTHROPIC_MODEL")
    api_key = os.getenv("ANTHROPIC_API_KEY")
    api_provider = "https://api.anthropic.com"


# 示例工具
@tangyuanAI.tool_registry.register_tool(
    allowed_agents=["api_demo_agent"],
    name="echo",
    description="原样回显用户输入（演示用）",
    parameters={
        "type": "object",
        "properties": {"text": {"type": "string", "description": "要回显的内容"}},
        "required": ["text"],
    },
)
def echo(text: str) -> str:
    return f"echo: {text}"


# 在 import 时自动激活（让 GET /agents 立即能看到）
activate_template("api_demo_agent")
activate_template("api_claude_agent")