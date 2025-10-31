import json
import os
import platform
import requests
import re
import sys
from abc import ABC, abstractmethod          # 新增
from bs4 import BeautifulSoup

class Agent(ABC):
    """
    抽象基类，所有具体 Agent 必须实现四个抽象属性：
        api_key
        api_provider
        model_name
        prompt
    """
    # ---------------- 抽象属性 ----------------
    @property
    @abstractmethod
    def api_key(self):        raise NotImplementedError
    @property
    @abstractmethod
    def api_provider(self):   raise NotImplementedError
    @property
    @abstractmethod
    def model_name(self):     raise NotImplementedError
    @property
    @abstractmethod
    def prompt(self):         raise NotImplementedError

    # ---------------- 通用构造 ----------------
    def __init__(self):
        self.uuid = self.__class__.uuid
        prompt = self.prompt + ", 你的uuid " + str(self.uuid)
        print(prompt)
        self.history = [{"role": "system", "content": prompt}]
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        self.os_name = platform.system()
        self.conversations_folder = os.getcwd()
        if self.os_name == "Windows":
            self.os_main_folder = os.getenv("USERPROFILE")
        elif self.os_name == "Linux":
            self.os_main_folder = os.path.expanduser("~")
        elif self.os_name == "Darwin":
            self.os_main_folder = os.getenv("HOME")

        if not self.Connectivity():
            raise ConnectionError("请检查api_provider，model_name，api_key")

    # ---------------- 连通性测试 ----------------
    def Connectivity(self):
        self.history.append({"role": "user", "content": "你好"})
        payload = {
            "model": self.model_name,
            "messages": self.history,
            "stream": True,
            "stream_options": {"include_usage": True}
        }
        rsp = requests.post(self.api_provider,
                            headers=self.headers,
                            json=payload)
        self.history = [{"role": "system", "content": self.prompt}]
        return rsp.status_code == 200

    # ---------------- 主对话函数 ----------------
    def conversation_with_tool(self, messages=None) -> str:
        print(messages)
        if messages:
            self.history.append({"role": "user", "content": messages})
        payload = {
            "model": self.model_name,
            "messages": self.history,
            "stream": True,
            "stream_options": {"include_usage": True}
        }
        rsp = requests.post(
            self.api_provider,
            headers={**self.headers,
                     "Accept-Charset": "utf-8",
                     "Accept": "text/event-stream"},
            json=payload,
            stream=True
        )
        rsp.encoding = 'utf-8'

        # ---------- 流式收数据 ----------
        full_content = ""
        for line in rsp.iter_lines(decode_unicode=True):
            if not line or not line.startswith('data: '):
                continue
            data = line[6:]
            if data == '[DONE]':
                break
            try:
                chunk = json.loads(data)
            except json.JSONDecodeError:
                continue

            with open(os.path.join("./output", "log.log"), "w") as f:
                f.write(json.dumps(chunk, ensure_ascii=False, indent=2))
            delta = (chunk.get('choices') or [{}])[0].get('delta') or {}
            content = delta.get('content', '')
            if content:
                full_content += content
                print(content, end='', flush=True)

            usage = chunk.get('usage')
            if usage:
                print(f"\n本次请求用量：提示 {usage['prompt_tokens']} tokens，"
                      f"生成 {usage['completion_tokens']} tokens，"
                      f"总计 {usage['total_tokens']} tokens。")

        # ---------- 工具调用 ----------
        clean_pattern = re.compile(r'</?(out_text|thinking)>', flags=re.S)
        xml_pattern = re.compile(r'<(\w+)>.*?</\1>', flags=re.S)
        clean_content = clean_pattern.sub('', full_content)
        xml_blocks = [m.group(0) for m in xml_pattern.finditer(clean_content)]

        tool_results = []
        for block in xml_blocks:
            print("\n发现工具块:", block)
            soup = BeautifulSoup(block, "xml")
            root = soup.find()
            if root is None:
                raise ValueError("空 XML")
            tool_name = root.name
            if not hasattr(self, tool_name):          # 在本类里找工具函数
                raise AttributeError(f"类里找不到工具函数 {tool_name}")
            func = getattr(self, tool_name)
            result = func(block)
            tool_results.append(result)

        # 把助手回复存历史
        self.history.append({"role": "assistant", "content": full_content})

        if "<attempt_completion>" in full_content:
            print("\n[系统] AI 已标记任务完成，程序退出。")
            sys.exit(0)

        if tool_results:
            print("成功执行:", tool_results)
            self.history.extend(tool_results)
            print(self.history)
            return self.conversation_with_tool()

        return full_content

    # =================================================================
    #  以下区域 = 以前 tools.py 里的所有函数，直接搬进类里当实例方法
    # =================================================================
    def ask_for_help(self, xml_block: str):
        """
        实例方法版 ask_for_help，可直接访问 self.__class__.agent_list
        """
        from bs4 import BeautifulSoup   # 方法内 import 避免循环
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
            from Agent import agent_list

            target_cls = agent_list[agent_id]
            sender_cls = agent_list[send_id]
        except KeyError as e:
            return {"role": "system", "content": f"未找到 uuid/别名 {e}"}

        target_ins = target_cls()
        reply = target_ins.conversation_with_tool(
            {"role": agent_id, "content": message}
        )
        return {"role": agent_id, "content": reply}
