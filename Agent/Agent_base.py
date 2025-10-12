import json
import os
import platform
import requests
import re
import sys
from bs4 import BeautifulSoup          # 仅依赖 BS4+lxml

# 动态导入 tool.py
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import tool


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

            if 'choices' in chunk and chunk['choices']:
                delta = chunk['choices'][0].get('delta') or {}
                content = delta.get('content', '')
                if content:
                    full_content += content
                    print(content, end='', flush=True)

            if 'usage' in chunk:
                u = chunk['usage']
                print(f"\n本次请求用量：提示 {u['prompt_tokens']} tokens，"
                      f"生成 {u['completion_tokens']} tokens，"
                      f"总计 {u['total_tokens']} tokens。")

        # ======== 工具调用阶段 ========
        clean_pattern = re.compile(r'</?(out_text|thinking)>', flags=re.S)
        xml_pattern = re.compile(r'<(\w+)>.*?</\1>', flags=re.S)

        clean_content = clean_pattern.sub('', full_content)
        xml_blocks = [m.group(0) for m in xml_pattern.finditer(clean_content)]

        tool_results = []
        for block in xml_blocks:
            print("\n发现工具块:", block)
            try:
                soup = BeautifulSoup(block, "xml")
                root = soup.find()
                if root is None:
                    raise ValueError("空 XML")
                tool_name = root.name

                # 动态取函数
                if not hasattr(tool, tool_name):
                    raise AttributeError(f"tool.py 里没有函数 {tool_name}")

                func = getattr(tool, tool_name)

                # 把 XML 块直接丢给函数，让函数自己解析；也可以按需改传参
                result = func(block)          # 调用 tool.py 里的同名函数
                tool_results.append(str(result))
            except Exception as e:
                tool_results.append(f"工具异常：{e}")

        if tool_results:
            self.history.append({"role": "system",
                                 "content": "工具返回：\n" + "\n".join(tool_results)})

        self.history.append({"role": "assistant", "content": full_content})

        if "<attempt_completion>" in full_content:
            print("\n[系统] AI 已标记任务完成，程序退出。")
            exit(0)

        return full_content