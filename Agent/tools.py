# tools.py
from typing import Any
from bs4 import BeautifulSoup
import Agent

def ask_for_help(xml_block: str):
    soup = BeautifulSoup(xml_block, "xml")

    agent_id_tag = soup.find("agent_id")
    message_tag  = soup.find("message")
    send_id_tag  = soup.find("your_id")

    if agent_id_tag is None:
        return {"role": "system","content": "<ask_for_help> 缺少 agent_id 字段"}
    if message_tag is None:
        return {"role": "system", "content": "<ask_for_help> 缺少 message 字段"}
    if send_id_tag is None:
        return {"role": "system", "content": "<ask_for_help> 缺少 your_id 字段"}

    # 全部转字符串
    agent_id = agent_id_tag.text.strip()
    message  = message_tag.text.strip()
    send_id  = send_id_tag.text.strip()

    # 取类 → 实例化 → 调用
    try:
        target_cls = Agent.agent_list[agent_id]
        sender_cls = Agent.agent_list[send_id]
    except KeyError as e:
        return {"role": "system", "content": f"未找到 uuid/别名 {e}"}

    target_ins   = target_cls()            # 新建接收方实例

    # 让接收方回答，并把回答追加到发送方历史
    reply = target_ins.conversation_with_tool(
        f"{message} ——来自{send_id}"
    )
    return {"role": "assistant","content": {agent_id: reply}}
