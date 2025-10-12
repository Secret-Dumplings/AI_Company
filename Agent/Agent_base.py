import json
import os
import platform
import requests
import re
import sys
from bs4 import BeautifulSoup          # 仅依赖 BS4+lxml
from . import tools


class Agent:
    # ====== 以下所有 __init__ 内容保持你原来逻辑不变 ======
    def __init__(self):
        if not self.api_key:
            raise KeyError("没有找到api_key")
        if not self.api_provider:
            raise KeyError("没有api_provider")
        if not self.model_name:
            raise KeyError("没有model_name")
        if not self.prompt:
            raise KeyError("没有prompt")

        self.history = [{"role": "system", "content": self.prompt}]
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

    # ================= 连通性测试 =================
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

    # ================= 主对话函数 =================
    def conversation_with_tool(self, messages=None) -> str:
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

        # ---------------- 流式收数据阶段 ----------------
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

            # 1. 拼内容
            delta = (chunk.get('choices') or [{}])[0].get('delta') or {}
            content = delta.get('content', '')
            if content:
                full_content += content
                print(content, end='', flush=True)

            # 2. 用量打印（不再这里判断结束！）
            usage = chunk.get('usage')
            if usage:
                print(f"\n本次请求用量：提示 {usage['prompt_tokens']} tokens，"
                      f"生成 {usage['completion_tokens']} tokens，"
                      f"总计 {usage['total_tokens']} tokens。")

        # ---------------- 工具调用阶段（一定执行） ----------------
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
            if not hasattr(tools, tool_name):
                raise AttributeError(f"tools.py 里没有函数 {tool_name}")
            func = getattr(tools, tool_name)
            result = func(block)
            tool_results.append(result)

        # 再把助手回复存历史
        self.history.append({"role": "assistant", "content": full_content})

        if "<attempt_completion>" in full_content:
            print("\n[系统] AI 已标记任务完成，程序退出。")
            exit(0)
        if xml_blocks:
            exit(0)

        if tool_results:
                print("成功执行:",tool_results)
                self.history.extend(tool_results)
                print(self.history)
                self.conversation_with_tool()

        return full_content