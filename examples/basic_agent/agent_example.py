# -*- coding: utf-8 -*-
"""
基础 Agent 示例

此示例展示如何：
1. 注册自定义工具
2. 创建 Agent 类
3. 使用 Agent 进行对话
"""
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import Dumplings
import uuid


# 1. 注册工具
@Dumplings.tool_registry.register_tool(
    allowed_agents=["time_agent_uuid", "time_agent"],
    name="get_time",
    description="获取当前时间",
    parameters={
        "type": "object",
        "properties": {},
        "required": []
    }
)
def get_time():
    """获取当前时间的工具函数"""
    return "11:03"


# 2. 创建调度 Agent
@Dumplings.register_agent(uuid.uuid4().hex, "scheduling_agent")
class SchedulingAgent(Dumplings.BaseAgent):
    """
    调度 Agent 示例

    功能：
    - 可以与其他 Agent 通讯
    - 可以使用工具
    - 支持 Function Calling 模式
    """
    prompt = "你是一个名为汤圆 Agent 的 AGI"
    api_provider = "https://coding.dashscope.aliyuncs.com/v1/chat/completions"
    model_name = "qwen3.5-plus"
    api_key = os.getenv("API_KEY")
    fc_model = True  # 启用 Function Calling 模式

    def __init__(self):
        super().__init__()

    def out(self, content):
        """自定义输出处理"""
        if content.get("tool_name"):
            print("调用工具:", content.get("tool_name"), "参数", content.get("tool_parameter"))
            return
        if not content.get("task"):
            print(content.get("message"), end="")
        else:
            print()


# 3. 创建时间 Agent
@Dumplings.register_agent("time_agent_uuid", "time_agent")
class TimeAgent(Dumplings.BaseAgent):
    """
    时间 Agent 示例

    功能：
    - 可以使用 get_time 工具查询时间
    - 可以与其他 Agent 协作
    """
    prompt = "你是一个名为汤圆 Agent 的 AGI 的子 agent 名为时间管理者，你可以通过工具获取时间"
    api_provider = "https://coding.dashscope.aliyuncs.com/v1/chat/completions"
    model_name = "qwen3.5-plus"
    api_key = os.getenv("API_KEY")

    def __init__(self):
        super().__init__()


# 4. 运行示例
if __name__ == "__main__":
    # 获取调度 Agent 实例
    schedule_agent = Dumplings.agent_list["scheduling_agent"]

    # 运行对话
    print("=== 基础 Agent 示例 ===")
    print("开始对话...\n")

    # 示例：请求时间 Agent 查询时间
    schedule_agent.conversation_with_tool(
        "你现在有一个 id 为 time_agent_uuid 的同伴，请求它帮你查看现在时间"
    )