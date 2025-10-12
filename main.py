from dotenv import load_dotenv
import os
import Agent
import uuid

load_dotenv()

@Agent.register_agent(uuid.uuid4().hex, "scheduling_agent")
class scheduling_agent(Agent.BaseAgent):
    def __init__(self):
        self.prompt = "你是一个名为汤圆Agent的AGI，你可以用<ask_for_help><agent_id>id</agent_id></ask_for_help>的方式寻求其他Agent帮助"
        self.api_provider = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
        self.model_name = "qwen3-max"
        self.api_key = os.getenv("API_KEY")
        super().__init__()

schedule_agent = Agent.agent_list["scheduling_agent"]()
# schedule_agent.conversation_with_tool("你好")
schedule_agent.conversation_with_tool("你现在有一个id为8841cd45eef54217bc8122cafebe5fd6的同伴，请求它帮忙")
