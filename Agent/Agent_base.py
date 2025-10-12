import json
import os
import platform
import requests
import re

class Agent():
    def __init__(self):
        if not self.api_key:
            raise KeyError("没有找到api_key")
        if not self.api_provider:
            raise KeyError("没有api_provider")
        if not self.model_name:
            raise KeyError("没有model_name")
        if not self.prompt:
            raise KeyError("没有prompt")
        self.history = []
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        self.os_name = platform.system()
        self.conversations_folder = os.getcwd()
        if self.os_name == "Windows":
            self.os_main_folder = os.getenv("USERPROFILE")
        if self.os_name == "Linux":
            self.os_main_folder = os.path.expanduser("~")
        if self.os_name == "Darwin":
            self.os_main_folder = os.getenv("HOME")
        if not self.Connectivity():
            raise ConnectionError("请检查api_provider，model_name，api_key")
        self.history.append({
        "role":"system",
        "content":f"{self.prompt}"
        })


    def Connectivity(self):
        self.history.append(
        {
        "role":"user",
        "content":"你好"
        })
        request_body = {
            "model": self.model_name,
            "messages": self.history,
            "stream": True,
            "stream_options":{
                "include_usage": True
            }
        }

        response = requests.post(
            self.api_provider,
            headers=self.headers,
            json=request_body
        )
        self.history = [
        {
        "role":"system",
        "content":f"{self.prompt}"
        }]
        if response.status_code != 200:
            return False


        return True
    def conversation_with_tool(self, messages = None) -> str:
        if messages:
            self.history.append({"role": "user", "content": messages})
        request_body = {
            "model": self.model_name,
            "messages": self.history,
            "stream": True,
            "stream_options": {"include_usage": True}
        }

        response = requests.post(
            self.api_provider,
            headers={
                **self.headers,
                "Accept-Charset": "utf-8",
                "Accept": "text/event-stream"
            },
            json=request_body,
            stream=True
        )
        response.encoding = 'utf-8'
        full_content = ""
        for line in response.iter_lines(decode_unicode=True):
            if not line:
                continue
            line = line.strip()
            if not line.startswith('data: '):
                continue

            data = line[6:]
            if data == '[DONE]':
                break
            try:
                chunk = json.loads(data)
            except json.JSONDecodeError:
                continue

            choices = chunk.get('choices')
            if choices and len(choices) > 0:
                delta = choices[0].get('delta') or {}
                content = delta.get('content', '')
                if content:
                    full_content += content
                    print(content, end='', flush=True)
                continue

            if 'usage' in chunk:
                usage = chunk['usage']
                usage_msg = (
                    f"\n本次请求用量："
                    f"提示 {usage['prompt_tokens']} tokens，"
                    f"生成 {usage['completion_tokens']} tokens，"
                    f"总计 {usage['total_tokens']} tokens。"
                )
                print(usage_msg)
                continue


        # ---------- 处理工具调用 ----------
        # 预编译正则表达式
        clean_pattern = re.compile(r'</?(out_text|thinking)>', flags=re.S)

        xml_pattern = re.compile(r'<(\w+)>.*?</\1>', flags=re.S)

        clean_content = clean_pattern.sub('', full_content)
        xml_blocks = [m.group(0) for m in xml_pattern.finditer(clean_content)]

        # 一次性执行所有工具，并把结果汇总
        tool_results = []
        for block in xml_blocks:
            print("发现:", block)
            try:
                tool_results.append("暂时没有工具可调用")
            except Exception as e:
                tool_results.append(f"工具异常：{e}")

        if tool_results:
            # 把所有工具结果一次性给 AI，让它继续思考
            self.history.append({"role": "system",
                                 "content": "工具返回：\n" + "\n".join(tool_results)})
            # full_content = self.conversation_with_tool()  # 只再请求一次

        # 最终保存
        self.history.append({"role": "assistant", "content": full_content})

        # 只在这里判断是否结束
        if "<attempt_completion>" in full_content:
            print("\n[系统] AI 已标记任务完成，程序退出。")
            exit(0)

        return full_content