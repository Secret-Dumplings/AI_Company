from dotenv import load_dotenv
import os
import Agent
import uuid

load_dotenv()

@Agent.register_agent(uuid.uuid4().hex, "scheduling_agent")
class scheduling_agent(Agent.BaseAgent):
    def __init__(self):
        self.uuid = self.__class__.uuid
        self.prompt = f"你是一个名为汤圆Agent的AGI，你可以用<ask_for_help><agent_id>id</agent_id><message>message</message><your_id>your_id</your_id></ask_for_help>的方式与其他Agent通讯， 你的uuid为{self.uuid}"
        self.api_provider = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
        self.model_name = "qwen3-max"
        self.api_key = os.getenv("API_KEY")
        super().__init__()

@Agent.register_agent("8841cd45eef54217bc8122cafebe5fd6", "time_guide")
class time_agent(Agent.BaseAgent):
    def __init__(self):
        self.prompt = "你是一个名为汤圆Agent的AGI的子agent名为时间管理者，你可以用<ask_for_help><agent_id>id</agent_id><message>message</message></ask_for_help>的方式与其他Agent通讯， 现在的时间是16:15"
        self.api_provider = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
        self.model_name = "qwen3-max"
        self.api_key = os.getenv("API_KEY")
        super().__init__()

schedule_agent = Agent.agent_list["scheduling_agent"]()
# schedule_agent.conversation_with_tool("你好")
schedule_agent.conversation_with_tool("你现在有一个id为8841cd45eef54217bc8122cafebe5fd6的同伴，请求它帮你查看现在时间")
