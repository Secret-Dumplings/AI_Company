import Agent
import uuid
import os
from dotenv import load_dotenv

load_dotenv()

@Agent.register_agent(uuid.uuid4().hex, "scheduling_agent")
class scheduling_agent(Agent.BaseAgent):
    def __init__(self):
        self.prompt = "你是一个名为汤圆Agent的AGI, 你可以用<request_Agent><uuid>uuid</uuid></request_Agent>的方式请求其他Agent"
        self.api_provider = "https://api-inference.modelscope.cn/v1/chat/completions"
        self.model_name = "Qwen/Qwen3-Coder-480B-A35B-Instruct"
        self.api_key = os.getenv("API_KEY")
        super().__init__()

schedule_agent = Agent.agent_list["scheduling_agent"]()
schedule_agent.conversation_with_tool("你好，你现在有一个名为1c04ff44be9c4211bee0c58a385f23c3的AI同伴，请向他咨询现在天气")