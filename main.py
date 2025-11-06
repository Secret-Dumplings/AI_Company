import sys

from dotenv import load_dotenv
import os
import Dumplings
import uuid
# from Dumplings import tool_registry

load_dotenv()

@Dumplings.register_agent(uuid.uuid4().hex, "scheduling_agent")
class scheduling_agent(Dumplings.BaseAgent):
    prompt = f"你是一个名为汤圆Agent的AGI，你可以用<ask_for_help><agent_id>id</agent_id><message>message</message></ask_for_help>的方式与其他Agent通讯, 你可以使用<attempt_completion>标签退出对话， 它的语法为<attempt_completion><report_content>放入你想播报的内容，或留空</report_content></attempt_completion>"
    api_provider = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    model_name = "qwen3-max"
    api_key = os.getenv("API_KEY")
    def __init__(self):
        super().__init__()

@Dumplings.register_agent("8841cd45eef54217bc8122cafebe5fd6", "time_guide")
class time_agent(Dumplings.BaseAgent):
    prompt = "你是一个名为汤圆Agent的AGI的子agent名为时间管理者，你可以用<ask_for_help><agent_id>id</agent_id><message>message</message></ask_for_help>的方式与其他Agent通讯， 现在的时间是16:15"
    api_provider = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    model_name = "qwen3-max"
    api_key = os.getenv("API_KEY")
    def __init__(self):
        super().__init__()

from Dumplings import tool_registry

print("注册的工具列表：")
for name, info in tool_registry.list_tools().items():
    print(f"工具：{name}，允许的 agents：{info['allowed_agents']}")

print("UUID 映射表：")
print(tool_registry._uuid_to_name)

schedule_agent = Dumplings.agent_list["scheduling_agent"]
# schedule_agent.conversation_with_tool("你好")
schedule_agent.conversation_with_tool("你现在有一个id为8841cd45eef54217bc8122cafebe5fd6的同伴，请求它帮你查看现在时间")


#tools
@Dumplings.tool_registry.register_tool(
    allowed_agents=None,
    description="""
        一、语法结构（Syntax）
        该函数用于一个 Dumplings 向另一个 Dumplings 发起请求，使用 XML 格式 描述请求内容。
        正确语法格式：
        <request>
            <agent_id>目标Agent的ID</agent_id>
            <message>你要发送的消息内容</message>
        </request>
        注意事项：
        所有标签必须 成对出现，且 大小写敏感。
        必须包含 <agent_id> 和 <message> 两个字段。
        XML 标签不能交叉嵌套，必须正确闭合。
        二、功能作用（Purpose）
        ask_for_help 是 Dumplings 之间通信的桥梁，主要实现以下功能：
        | 功能点 | 说明 |
        | --- | --- | 
        | 跨Agent通信 | 允许一个 Dumplings 向另一个指定 Dumplings 发送消息。 |
        | 任务协作 | 支持任务分发、请求处理、结果返回等协作行为。 |
        | 自动路由 | 系统根据 agent_id 自动找到目标 Dumplings 并转发消息。 |
        | 上下文记录	请求和响应会自动记录到当前 Dumplings 的 history 中，便于后续追踪。 |
        三、使用效果（Effect）
        成功调用后：
        目标 Dumplings 收到消息并处理。
        当前 Dumplings 收到目标 Dumplings 的响应内容。
        响应内容会自动追加到当前 Dumplings 的历史记录中，格式如下：
        {"role": "assistant", "content": "目标Agent的回复内容"}
        调用失败时：
        系统将返回一个错误提示，格式如下：
        {"role": "system", "content": "错误信息"}
        常见错误包括：
        缺少 <agent_id> 或 <message> 标签
        找不到目标 Dumplings
        当前 Dumplings 没有设置 uuid
        四、使用示例（Example）
        示例 1：向 Dumplings "writer" 请求撰写文章
        <request>
            <agent_id>writer</agent_id>
            <message>请帮我写一篇关于人工智能的科普文章</message>
        </request>
        效果：
        系统会将消息发送给 ID 为 writer 的 Dumplings，并返回其生成的文章内容。
        示例 2：向 Dumplings "coder" 请求生成代码
        <request>
            <agent_id>coder</agent_id>
            <message>请用Python写一个快速排序函数</message>
        </request>
        效果：
        系统会将请求发送给 coder，并返回排序函数的代码。
        五、Dumplings 使用建议（Best Practice）
        使用标准 XML 格式	保证标签闭合、嵌套正确，避免解析失败。
        明确目标 Dumplings ID	确保 agent_id 在系统中唯一且已注册。
        消息内容简洁清晰	提高目标 Dumplings 的理解和处理效率。
        检查返回内容	判断是否为错误提示，避免误用无效结果。
        六、总结（Summary）
        ask_for_help 是 Dumplings 之间协作的核心通信接口，采用 XML 格式描述请求，具备自动路由、上下文记录和错误处理机制。正确使用该函数，可实现高效、灵活的多 Dumplings 协作系统。
    """,
    name="ask_for_help"
)
def ask_for_help(self, xml_block: str):
    """
    实例方法版 ask_for_help，可直接访问 self.__class__.agent_list
    """
    from bs4 import BeautifulSoup  # 方法内 import 避免循环
    soup = BeautifulSoup(xml_block, "xml")

    agent_id_tag = soup.find("agent_id")
    message_tag = soup.find("message")
    send_id_tag = self.uuid

    if agent_id_tag is None:
        return {"role": "system", "content": "<ask_for_help> 缺少 agent_id 字段"}
    if message_tag is None:
        return {"role": "system", "content": "<ask_for_help> 缺少 message 字段"}
    if send_id_tag is None:
        return {"role": "system", "content": "<ask_for_help> 缺少 your_id 字段"}

    agent_id = agent_id_tag.text.strip()
    message = message_tag.text.strip()
    send_id = send_id_tag

    try:
        from Dumplings import agent_list

        target_cls = agent_list[agent_id]
        sender_cls = agent_list[send_id]
    except KeyError as e:
        return {"role": "system", "content": f"未找到 uuid/别名 {e}"}

    target_ins = target_cls
    reply = target_ins.conversation_with_tool(message)
    self.history.append({"role": "assistant", "content": reply})
    return reply

@Dumplings.tool_registry.register_tool(
    allowed_agents=None,
    description="""
        一、语法结构（Syntax）
        该函数用于处理 XML 格式的完成报告，提取并输出报告内容。
        ✅ 正确语法格式：
        xml
        复制
        <report>
            <report_content>
                这里填写任务完成的详细报告内容
            </report_content>
        </report>
        ⚠️ 语法要求：
        必须包含 <report_content> 标签
        标签必须正确闭合
        内容放在 <report_content> 和 </report_content> 之间
        二、功能作用（Purpose）
        attempt_completion 是 Dumplings 报告任务完成情况的标准接口，主要实现以下功能：
        表格
        复制
        功能点	说明
        报告解析	自动解析 XML 格式的完成报告
        内容提取	提取 <report_content> 标签内的文本内容
        结果输出	将报告内容输出到标准输出流
        错误处理	如果格式错误或内容缺失，会输出错误提示
        三、使用效果（Effect）
        ✅ 成功调用后：
        报告内容会被输出到标准输出
        函数返回 True 表示成功
        输出示例：
        复制
        任务完成报告：
        - 处理文件：100个
        - 成功：95个
        - 失败：5个
        - 错误率：5%
        ❌ 调用失败时：
        错误信息会输出到标准错误流
        函数返回 False 表示失败
        错误示例：
        警告: 未找到 report_content 标签
        四、使用示例（Example）
        示例 1：标准完成报告
        xml
        复制
        <report>
            <report_content>
                数据分析任务已完成：
                - 处理数据：1000条
                - 有效数据：980条
                - 无效数据：20条
                - 处理时间：15秒
            </report_content>
        </report>
        效果：
        系统会输出完整的报告内容，并返回成功状态。
        示例 2：简洁完成报告
        xml
        复制
        <report>
            <report_content>代码生成任务完成，共生成5个Python函数</report_content>
        </report>
        效果：
        输出：代码生成任务完成，共生成5个Python函数
        示例 3：带格式的报告
        xml
        复制
        <report>
            <report_content>
                === 图像处理报告 ===
                输入图像：50张
                成功处理：48张
                失败：2张（格式不支持）
                平均处理时间：0.3秒/张
            </report_content>
        </report>
        效果：
        保持原有格式输出完整的报告内容。
        五、常见错误（Common Errors）
        ❌ 错误 1：缺少必要标签
        xml
        复制
        <report>
            <status>completed</status>
        </report>
        结果：
        输出错误：未找到 report_content 标签
        ❌ 错误 2：标签未闭合
        xml
        复制
        <report>
            <report_content>
                任务完成
            <!-- 缺少 </report_content> 和 </report> -->
        结果：
        XML解析错误，函数返回失败
        ❌ 错误 3：空内容
        xml
        复制
        <report>
            <report_content></report_content>
        </report>
        结果：
        输出错误：report_content 标签内容为空
        六、Dumplings 使用建议（Best Practice）
        表格
        复制
        建议	说明
        ✅ 使用标准 XML 格式	确保标签闭合、格式正确
        ✅ 内容清晰具体	报告应包含关键信息：任务类型、处理数量、结果统计等
        ✅ 适当的格式化	使用换行符、缩进等提高可读性
        ✅ 检查返回值	确认报告是否成功处理
        七、总结（Summary）
        attempt_completion 是 Dumplings 完成任务后提交报告的标准接口，采用 XML 格式描述报告内容，具备自动解析、内容提取和错误处理功能。正确使用该函数，可实现标准化的任务完成报告机制。
        适用对象： 所有支持 attempt_completion 接口的 Dumplings 实例
        推荐场景： 任务完成报告、状态汇报、结果统计、执行摘要等
    """,
    name="attempt_completion"
)
def attempt_completion(self, xml_block: str):
    from bs4 import BeautifulSoup  # 方法内 import 避免循环
    soup = BeautifulSoup(xml_block, "xml")

    report_content_tag = soup.find("report_content")

    if report_content_tag is None:
        sys.exit(0)

    print(report_content_tag.strip())


