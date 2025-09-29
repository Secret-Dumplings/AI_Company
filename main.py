import Agent
import uuid



@Agent.register_agent(uuid.uuid4().hex, "scheduling_agent")
class scheduling_agent(Agent.BaseAgent):
    def __init__(self):
        self.prompt = "你是一个名为汤圆Agent的AGI"
        self.api_provider = "https://api-inference.modelscope.cn/v1/chat/completions"
        self.model_name = "Qwen/Qwen3-Coder-480B-A35B-Instruct"
        self.api_key = 'ms-84fd9d0c-e7a2-4964-8efd-a9117f93caa3'
        super().__init__()

schedule_agent = Agent.agent_list["scheduling_agent"]()
schedule_agent.conversation_with_tool("你好")