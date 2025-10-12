import os
import Agent
import uuid



@Agent.register_agent(uuid.uuid4().hex, "scheduling_agent")
class scheduling_agent(Agent.BaseAgent):
    def __init__(self):
        self.prompt = "你是一个名为汤圆Agent的AGI"
        self.api_provider = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
        self.model_name = "qwen3-max"
        self.api_key = os.environ.get("API_KEY")
        super().__init__()

schedule_agent = Agent.agent_list["scheduling_agent"]()
schedule_agent.conversation_with_tool("你好")