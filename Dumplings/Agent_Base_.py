import json
import os
import platform
import requests
import re
import sys
from abc import ABC, abstractmethod
from bs4 import BeautifulSoup
from loguru import logger #配置日志

try:
    from .agent_tool import tool_registry
except:
    raise ImportError("不可单独执行")
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
        self.name=self.__class__.name
        self.stream_run=False
        self.stream = True
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
            "stream": self.stream,
            "stream_options": {"include_usage": True}
        }
        rsp = requests.post(self.api_provider,
                            headers=self.headers,
                            json=payload)
        self.history = [{"role": "system", "content": self.prompt}]
        return rsp.status_code == 200

    # ---------------- 主对话函数 ----------------
    def conversation_with_tool(self, messages=None,tool=False):
        if messages:
            self.history.append({"role": "user", "content": messages})
        payload = {
            "model": self.model_name,
            "messages": self.history,
            "stream": self.stream,
            "stream_options": {"include_usage": True}
        }
        rsp = requests.post(
            self.api_provider,
            headers={**self.headers,
                     "Accept-Charset": "utf-8",
                     "Accept": "text/event-stream"},
            json=payload,
            stream=self.stream
        )
        rsp.encoding = 'utf-8'

        full_content = ""
        self.stream_run = True
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
                self.pack(content,finish_task=False)
            usage = chunk.get('usage')
            if usage:
                self.stream_run = False
                self.pack(finish_task=True)
                self.pack(f"\n本次请求用量：提示 {usage['prompt_tokens']} tokens，"
                      f"生成 {usage['completion_tokens']} tokens，"
                      f"总计 {usage['total_tokens']} tokens。", other=True)
        logger.info(full_content)

        # 1. 去掉工具块后再存历史，防止循环触发
        xml_pattern = re.compile(r'<(\w+)>.*?</\1>', flags=re.S)
        # clean_for_history = xml_pattern.sub('', full_content).strip()
        # self.history.append({"role": "assistant", "content": clean_for_history})

        # 2. 提取并执行工具
        clean_pattern = re.compile(r'</?(out_text|thinking)>', flags=re.S)
        clean_content = clean_pattern.sub('', full_content)
        xml_blocks = [m.group(0) for m in xml_pattern.finditer(clean_content)]
        tool_results = []
        tool_names = []
        for block in xml_blocks:
            logger.info("\n发现工具块:" + str(block))
            soup = BeautifulSoup(block, "xml")
            root = soup.find()
            if root is None:
                raise ValueError("空 XML")
            tool_name = root.name

            # 优先级查找工具：1. 工具注册器 2. 类方法 3. 返回无工具
            tool_func = None
            tool_source = None

            # 优先级1: 在工具注册器中查找
            if tool_registry.check_permission(self.uuid, tool_name):
                tool_info = tool_registry.get_tool_info(tool_name)
                if tool_info is not None:
                    tool_func = tool_info['function']
                    tool_source = "工具注册器"

            # 优先级2: 在类方法中查找
            if tool_func is None and hasattr(self, tool_name):
                method = getattr(self, tool_name)
                if callable(method):
                    tool_func = method
                    tool_source = "类方法"

            # 优先级3: 都没有找到
            if tool_func is None:
                available_tools = self._get_all_available_tools()
                tool_error = f"工具错误：找不到工具 '{tool_name}'。"
                if available_tools:
                    tool_error += f" 你可以使用以下工具：{', '.join(available_tools)}"

                self.history.append({"role": "system", "content": tool_error})
                tool_results.append({"error": tool_error})
                logger.warning(f"工具 {tool_name} 未找到，可用工具: {available_tools}")
                continue

            logger.info(f"从 {tool_source} 找到工具 {tool_name}")
            print(block)
            self.pack(tool_name= tool_name, tool_parameter=tool_func)

            # 执行工具
            # try:
            #获得报错回溯
            result = tool_func(block)
            tool_results.append(result)
            tool_names.append(tool_name)
            # except Exception as e:
            #     error_msg = f"执行工具 {tool_name} 时出错: {str(e)}"
            #     self.history.append({"role": "system", "content": error_msg})
            #     tool_results.append({"error": error_msg})
            #     logger.error(f"工具执行错误: {error_msg}")

        #如配置错误强制跳出避免堵塞
        if "<attempt_completion>" in full_content:
            self.pack("\n[系统] AI 已标记任务完成，程序退出。", tool_name="attempt_completion")
            sys.exit(0)

        # 3. 若工具产生结果，继续对话
        if tool_results:
            logger.info("成功执行" + str(tool_results))
            n = 0
            for i in tool_results:
                try:
                    self.history.append({"role": "system", "content": f"{tool_names[n]} results: {i}"})
                    n+=1
                except:
                    break
            logger.info("history:"+str(self.history))
            return self.conversation_with_tool(tool=True)
        if tool:
            logger.info(
                str(self.history)
            )
            return self.history[-1]
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

    def pack(self, message=None,tool_model=False, tool_name=None, tool_parameter=None, finish_task=False, other=False):
        content = {}
        if finish_task:
            content = {
                "task": True
            }
        elif tool_model:
            content = {
                "tool_name": tool_name,
                "tool_parameter": tool_parameter,
                "ai_uuid": self.uuid,
                "ai_name": self.name,
                "task": False
            }
        else:
            content = {
            "message": message,
            "ai_uuid": self.uuid,
            "ai_name": self.name,
            "other": other,
            "task": False
        }
        self.out(content)

    def out(self, content):
        if content.get("tool_name"):
            print("调用工具:", content.get("tool_name"),"参数", content.get("tool_parameter"))
            return
        if not content.get("task"):
            print(content.get("message"),end="")
        else:
            print()


    def ask_for_help(self, xml_block: str):
        """
        实例方法版 ask_for_help，可直接访问 self.__class__.agent_list
        """
        from bs4 import BeautifulSoup  # 方法内 import 避免循环
        soup = BeautifulSoup(xml_block, "xml")

        agent_id_tag = soup.find("agent_id")
        message_tag = soup.find("message")
        if agent_id_tag is None:
            # self.history.append({"role": "system", "content": "<ask_for_help> 缺少 agent_id 字段"})
            return {"role": "system", "content": "<ask_for_help> 缺少 agent_id 字段"}
        if message_tag is None:
            # self.history.append({"role": "system", "content": "<ask_for_help> 缺少 message 字段"})
            return {"role": "system", "content": "<ask_for_help> 缺少 message 字段"}

        agent_id = agent_id_tag.text.strip()
        message = message_tag.text.strip()

        try:
            from Dumplings import agent_list

            target_cls = agent_list[agent_id]
        except KeyError as e:
            # self.history.append({"role": "system", "content": f"未找到 uuid/别名 {e}"})
            return {"role": "system", "content": f"未找到 uuid/别名 {e}"}

        target_ins = target_cls
        reply = target_ins.conversation_with_tool(message)
        # self.history.append({"role": "assistant", "content": reply})
        return reply

    def attempt_completion(self, xml_block: str):
        from bs4 import BeautifulSoup  # 方法内 import 避免循环
        soup = BeautifulSoup(xml_block, "xml")

        report_content_tag = soup.find("report_content")

        if report_content_tag is None:
            sys.exit(0)

        print(report_content_tag)
        sys.exit(0)

