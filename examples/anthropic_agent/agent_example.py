# -*- coding: utf-8 -*-
"""
Anthropic 协议 Agent 示例

此示例展示：
1. 如何用 Dumplings.AnthropicAgent 走 Anthropic Messages API
2. 注册工具 + 让 Agent 自动调用
3. 与 BaseAgent 完全一致的使用体验（ask_for_help / list_agents / attempt_completion 都通用）

使用：
    export ANTHROPIC_API_KEY=sk-ant-xxx
    uv run python examples/anthropic_agent/agent_example.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import uuid

import Dumplings
from Dumplings.anthropic_agent import AnthropicAgent


# 1. 注册工具 —— 与 BaseAgent 共用同一套 tool_registry
@Dumplings.tool_registry.register_tool(
    allowed_agents=["weather_agent"],
    description="查询某城市的天气信息，返回一句话预报",
    name="get_weather",
    parameters={
        "type": "object",
        "properties": {
            "city": {"type": "string", "description": "城市名，如 北京 / 上海"},
        },
        "required": ["city"],
    },
)
def get_weather(city: str) -> str:
    # 这里接真实天气 API；演示直接返回
    return f"{city}今天晴，温度 25°C，湿度 40%"


@Dumplings.tool_registry.register_tool(
    allowed_agents=["weather_agent"],
    description="把摄氏温度转换为华氏温度",
    name="celsius_to_fahrenheit",
    parameters={
        "type": "object",
        "properties": {
            "c": {"type": "number", "description": "摄氏温度值"},
        },
        "required": ["c"],
    },
)
def celsius_to_fahrenheit(c: float) -> str:
    f = c * 9 / 5 + 32
    return f"{c}°C = {f:.1f}°F"


# 2. 注册 Anthropic 协议 Agent
@Dumplings.register_agent(uuid.uuid4().hex, "weather_agent",
                          "天气查询与温度换算助手，调用 get_weather / celsius_to_fahrenheit")
class WeatherAgent(AnthropicAgent):
    """
    走 Anthropic Messages API 的天气 Agent。
    """
    prompt = (
        "你是一个名为汤圆 AI 的天气助手。"
        "当用户问天气时，调用 get_weather 工具获取结果；"
        "当用户希望把温度换成华氏时，调用 celsius_to_fahrenheit。"
        "完成后用 attempt_completion 汇报。"
    )
    api_provider = os.getenv("ANTHROPIC_BASE_URL", "https://api.anthropic.com")
    model_name = os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest")
    api_key = os.getenv("ANTHROPIC_API_KEY")
    max_tokens = 1024

    def __init__(self):
        super().__init__()
        # 注册一个工具调用钩子，把每次调用写到日志
        self.register_tool_hook(self._log_tool_call)

    def _log_tool_call(self, event_type, tool_name, tool_args, tool_result=None, task_id=None):
        if event_type == "before":
            print(f"\n[hook:before] -> {tool_name}({tool_args})")
        elif event_type == "after":
            preview = (str(tool_result)[:120] + "…") if tool_result and len(str(tool_result)) > 120 else tool_result
            print(f"[hook:after] {tool_name} -> {preview}")
        elif event_type == "error":
            print(f"[hook:error] {tool_name} 失败：{tool_result}")

    def out(self, content):
        """自定义输出：流式文本直接打，工具调用走 hook"""
        if content.get("tool_name"):
            return  # 由 hook 处理
        if content.get("task"):
            print(f"\n[完成] {content.get('message', '')}")
            return
        if content.get("message") is not None:
            print(content.get("message"), end="", flush=True)


if __name__ == "__main__":
    if not os.getenv("ANTHROPIC_API_KEY"):
        print("未设置 ANTHROPIC_API_KEY，跳过实际对话；只演示装饰器和收集器。")
        # 即便不联网，也能 inspect 已收集到的工具 schema
        tool_registry = Dumplings.tool_registry
        for s in tool_registry.collect_builtin_tools(Dumplings.agent_list["weather_agent"]):
            fn = s["function"]
            print(f"  - {fn['name']}: {fn['description']}")
        sys.exit(0)

    agent = Dumplings.agent_list["weather_agent"]
    print("=== Anthropic Agent 示例 ===\n")
    agent.conversation_with_tool("帮我查一下北京今天的天气，再把温度换成华氏度。")