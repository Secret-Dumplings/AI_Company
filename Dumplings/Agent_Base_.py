import json
import os
import platform
import requests
import re
import sys
from abc import ABC, abstractmethod
from bs4 import BeautifulSoup
from loguru import logger #配置日志
from .agent_tool import tool_registry
logger.add("logs/app.log", rotation="500 MB", retention="10 days", compression="zip")


class Agent(ABC):
    """
    抽象基类，所有具体 Dumplings 必须实现四个抽象属性：
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
        self.uuid=self.__class__.uuid
        from .agent_tool import tool_registry
        agent_name = getattr(self.__class__, 'name', None) or getattr(self.__class__, '__name__', None)
        if agent_name and self.uuid:
            tool_registry.register_agent_uuid(self.uuid, agent_name)
        prompt = self.prompt + ", 你的uuid " + str(self.uuid)
        logger.info("prompt:"+str(prompt))
        # print(prompt)
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
            delta = (chunk.get('choices') or [{}])[0].get('delta') or {}
            content = delta.get('content', '')
            if content:
                full_content += content
                self.out(content)
            usage = chunk.get('usage')
            if usage:
                self.out(f"\n本次请求用量：提示 {usage['prompt_tokens']} tokens，"
                      f"生成 {usage['completion_tokens']} tokens，"
                      f"总计 {usage['total_tokens']} tokens。")

        # 1. 去掉工具块后再存历史，防止循环触发
        xml_pattern = re.compile(r'<(\w+)>.*?</\1>', flags=re.S)
        clean_for_history = xml_pattern.sub('', full_content).strip()
        self.history.append({"role": "assistant", "content": clean_for_history})

        if "<attempt_completion>" in full_content:
            self.out("\n[系统] AI 已标记任务完成，程序退出。")
            sys.exit(0)

        # 2. 提取并执行工具
        clean_pattern = re.compile(r'</?(out_text|thinking)>', flags=re.S)
        clean_content = clean_pattern.sub('', full_content)
        xml_blocks = [m.group(0) for m in xml_pattern.finditer(clean_content)]
        tool_results = []
        for block in xml_blocks:
            logger.info("\n发现工具块:" + str(block))
            soup = BeautifulSoup(block, "xml")
            root = soup.find()
            if root is None:
                raise ValueError("空 XML")
            tool_name = root.name

            # 检查工具权限
            if not tool_registry.check_permission(self.uuid, tool_name):
                # 检查是否有类似工具可以推荐
                available_tools = self._get_available_tools_for_agent()
                similar_tools = self._find_similar_tools(tool_name, available_tools)

                permission_error = f"权限错误：Dumplings '{self.uuid}' 没有权限使用工具 '{tool_name}'。"
                if similar_tools:
                    permission_error += f" 你可以使用以下类似的工具：{', '.join(similar_tools)}"
                else:
                    permission_error += f" 你有权限使用的工具包括：{', '.join(available_tools)}"

                self.history.append({"role": "system", "content": permission_error})
                tool_results.append({"error": permission_error})
                continue

            tool_info = tool_registry.get_tool_info(tool_name)
            if tool_info is None:
                raise AttributeError(f"工具 {tool_name} 未注册")

            func = tool_info['function']
            result = func(block)
            tool_results.append(result)

        # 3. 若工具产生结果，继续对话
        if tool_results:
            logger.info("成功执行" + str(tool_results))
            return self.conversation_with_tool()
        return full_content

    def _get_available_tools_for_agent(self) -> list[str]:
        """获取当前agent有权限使用的所有工具"""
        available_tools = []
        for tool_name, tool_info in tool_registry.list_tools().items():
            if tool_registry.check_permission(self.name, tool_name):
                available_tools.append(tool_name)
        return available_tools

    def _find_similar_tools(self, tool_name: str, available_tools: list[str]) -> list[str]:
        """查找相似的工具名称"""
        # 简单的字符串匹配，可以根据需要实现更复杂的相似度算法
        similar_tools = []
        for available_tool in available_tools:
            if tool_name.lower() in available_tool.lower() or available_tool.lower() in tool_name.lower():
                similar_tools.append(available_tool)
        return similar_tools[:3]  # 最多返回3个相似工具

    def out(self, content: str):
        print(content, end='', flush=True)

    def out(self, content: str):
        print(content, end='', flush=True)
