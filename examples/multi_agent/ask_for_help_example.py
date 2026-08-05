# -*- coding: utf-8 -*-
"""
多 Agent 协作示例

此示例展示：
1. 如何创建多个 Agent
2. Agent 间如何使用 ask_for_help 进行通讯
3. Function Calling 与 XML 两种调用方式
"""
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import tangyuanAI
from tangyuanAI.Agent_list import activate_template
import uuid


# 工具：获取时间（支持 Function Calling 和 XML 两种方式）
@tangyuanAI.tool_registry.register_tool(
    allowed_agents=["time_agent", "assistant_agent"],
    name="get_time",
    description="获取当前时间",
    parameters={
        "type": "object",
        "properties": {},
        "required": []
    }
)
def get_time():
    """
    获取当前时间

    支持两种调用方式：
    - Function Calling: get_time()
    - XML: <get_time></get_time>
    """
    return "11:03"


# Agent 1: 时间 Agent
TIME_AGENT_UUID = "time_agent_uuid"
@tangyuanAI.template_agent(
    "time_agent",
    uuid=TIME_AGENT_UUID,
    description="时间 Agent：负责提供时间查询服务（可调用 get_time 工具）",
)
class TimeAgent(tangyuanAI.BaseAgent):
    """
    时间 Agent - 负责提供时间查询服务

    可以使用工具：
    - get_time: 获取当前时间
    """
    prompt = "你是一个名为汤圆 Agent 的子 Agent，名为时间管理者。你负责提供时间查询服务，当用户询问时间时，请使用 get_time 工具。"
    api_provider = "https://coding.dashscope.aliyuncs.com/v1/chat/completions"
    model_name = os.getenv("OPENAI_MODEL")
    api_key = os.getenv("API_KEY")

    def __init__(self):
        super().__init__()


# Agent 2: 助手 Agent（支持 ask_for_help）
ASSISTANT_AGENT_UUID = "assistant_agent_uuid"
@tangyuanAI.template_agent(
    "assistant_agent",
    uuid=ASSISTANT_AGENT_UUID,
    description="助手 Agent：负责协调其他 Agent，可请求 ask_for_help",
)
class AssistantAgent(tangyuanAI.BaseAgent):
    """
    助手 Agent - 负责协调其他 Agent

    可以使用：
    - ask_for_help: 请求其他 Agent 帮助（支持 Function Calling 和 XML 两种方式）
    - list_agents: 列出所有可用 Agent
    """
    prompt = """你是一个助手 Agent。当用户需要你完成某项任务时，你可以请求其他专业 Agent 的帮助。

你可以使用 ask_for_help 请求其他 Agent 帮助：
- Function Calling 方式：ask_for_help(agent_id="time_agent", message="请查询时间")
- XML 方式：<ask_for_help><agent_id>time_agent</agent_id><message>请查询时间</message></ask_for_help>
"""
    api_provider = "https://coding.dashscope.aliyuncs.com/v1/chat/completions"
    model_name = os.getenv("OPENAI_MODEL")
    api_key = os.getenv("API_KEY")
    fc_model = True  # 启用 Function Calling 模式

    def __init__(self):
        super().__init__()

    def out(self, content):
        """自定义输出处理"""
        if content.get("tool_name"):
            print(f"\n[工具调用] {content.get('tool_name')}")
            print(f"参数：{content.get('tool_parameter')}")
            return
        if content.get("message"):
            print(content.get("message"), end="")
        else:
            print()


# Agent 3: 调度 Agent（协调多个 Agent）
SCHEDULING_AGENT_UUID = str(uuid.uuid4())
@tangyuanAI.template_agent(
    "scheduling_agent",
    uuid=SCHEDULING_AGENT_UUID,
    description="调度 Agent：负责协调多个 Agent 完成用户的复杂任务",
)
class SchedulingAgent(tangyuanAI.BaseAgent):
    """
    调度 Agent - 负责协调多个 Agent 完成任务
    """
    prompt = """你是一个调度 Agent。你的任务是协调其他 Agent 完成用户的复杂任务。

可用的 Agent：
- time_agent (UUID: time_agent_uuid): 查询时间
- assistant_agent (UUID: assistant_agent_uuid): 通用助手

你可以使用 ask_for_help 请求其他 Agent 帮助。
"""
    api_provider = "https://coding.dashscope.aliyuncs.com/v1/chat/completions"
    model_name = os.getenv("OPENAI_MODEL")
    api_key = os.getenv("API_KEY")
    fc_model = True

    def __init__(self):
        super().__init__()


if __name__ == "__main__":
    print("=== 多 Agent 协作示例 ===\n")

    # v0.3.0+ 模板池：先激活再使用
    activate_template("time_agent")
    activate_template("assistant_agent")
    activate_template("scheduling_agent")

    # 获取助手 Agent 实例
    assistant = tangyuanAI.agent_list["assistant_agent"]

    # 示例 1: 请求时间 Agent 查询时间
    print("--- 示例 1: 查询时间 ---")
    assistant.conversation_with_tool("请帮我查询当前时间")

    print("\n\n=== 示例完成 ===")