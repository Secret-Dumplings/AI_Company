1/0 #执行删除禁止误处
import json
import sys
import time
import platform
from idlelib.outwin import file_line_pats
from pathlib import Path
from dotenv import load_dotenv
import mcp
import requests
import os
import platform
import subprocess
from typing import Any, List, Dict
import re
import ast
import xml.etree.ElementTree as ET
import inspect


class AppLogger:
    def __init__(self):
        """Initialize the logger with a file that will be cleared on startup."""
        os.makedirs('./logs', exist_ok=True)
        self.log_file = f"./logs/log.log"
        # Clear the log file on startup
        with open(self.log_file, 'w', encoding="utf-8") as f:
            f.write("")

    def log(self, message):
        """Log a message to both file and console."""

        # Log to file
        with open(self.log_file, 'a', encoding="utf-8") as f:
            f.write(time.strftime("%Y-%m-%d-%H:%M:%S:\n", time.localtime())+message + "\n")


logger = AppLogger()


class LLMChat:
    def __init__(self, conversations_folder):
        self.history = []
        self.api_key = self.get_api_key()
        self.model = self.get_model_name()
        self.base_url = "https://api-inference.modelscope.cn/v1/chat/completions"
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        self.os_name = platform.system()
        self.conversations_folder = conversations_folder
        if self.os_name == "Windows":
            self.os_main_folder = os.getenv("USERPROFILE")
        if self.os_name == "Linux":
            self.os_main_folder = os.path.expanduser("~")
        if self.os_name == "Darwin":
            self.os_main_folder = os.getenv("HOME")
        self.get_prompt()
        if not self.Connectivity():
            raise ConnectionError
        else:
            logger.log("成功连接")
        self.history.append({
        "role":"system",
        "content":f"{self.prompt}"
        })
        self.agent = Agent(self)

    def get_api_key(self) -> str:
        """Load the API key from an environment variable."""
        load_dotenv()
        api_key = os.getenv("MODELSCOPE_API_KEY")
        if not api_key:
            raise ValueError("未找到 MODELSCOPE_API_KEY 环境变量，请在 .env 文件中设置。")
        return api_key

    def get_model_name(self) -> str:
        """Get the model name from the environment variable."""
        load_dotenv()
        model_name = os.getenv("MODEL_NAME")
        if not model_name:
            raise ValueError("未找到 MODEL_NAME 环境变量，请在 .env 文件中设置。")
        return model_name

    def Connectivity(self):
        self.history.append(
        {
        "role":"user",
        "content":"你好"
        })
        request_body = {
            "model": self.model,
            "messages": self.history,
            "stream": True,
            "stream_options":{
                "include_usage": True
            }
        }

        response = requests.post(
            self.base_url,
            headers=self.headers,
            json=request_body
        )
        self.history = [
        {
        "role":"system",
        "content":f"{self.prompt}"
        }]
        if response.status_code != 200:
            logger.log(f"API request failed with status {response.status_code}: {response.text}")
            return False
            # raise Exception(f"API request failed with status {response.status_code}: {response.text}")

        return True

    def get_prompt(self):
        with open("prompt.md", "r", encoding="utf-8") as f:
            self.prompt = f.read()
        self.prompt = self.prompt.format(
            conversations_folder=self.conversations_folder,
            osname=self.os_name,
            os_main_folder=self.os_main_folder,
            mcp_server="没有连接任何mcp工具"
        )
        logger.log("系统提示词:\n" + self.prompt)

    def conversation(self, messages = None):
        if messages:
            self.history.append({
                "role": "user",
                "content": messages
            })

        request_body = {
            "model": self.model,
            "messages": self.history,
            "stream": True,
            "stream_options": {"include_usage": True}
        }
        response = requests.post(
            self.base_url,
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
                logger.log(f"非法 JSON：{data}")
                continue

            # 正常 delta 内容
            choices = chunk.get('choices')
            if choices and len(choices) > 0:
                delta = choices[0].get('delta') or {}
                content = delta.get('content', '')
                if content:
                    full_content += content
                    print(content, end='', flush=True)
                continue

            # usage（最后一个包）
            if 'usage' in chunk:
                usage = chunk['usage']
                print(f"\n本次请求用量："
                      f"提示 {usage['prompt_tokens']} tokens，"
                      f"生成 {usage['completion_tokens']} tokens，"
                      f"总计 {usage['total_tokens']} tokens。")
                logger.log(f"本次请求用量："
                      f"提示 {usage['prompt_tokens']} tokens，"
                      f"生成 {usage['completion_tokens']} tokens，"
                      f"总计 {usage['total_tokens']} tokens。")
                continue

            # 其余未知情况
            logger.log(f"收到未知 chunk：{chunk}")

        self.history.append({
            "role": "assistant",
            "content": full_content
        })
        return full_content

    def conversation_with_tool(self, messages = None) -> str:
        if not hasattr(self, 'agent'):
            self.agent = Agent(self)

        if messages:
            self.history.append({"role": "user", "content": messages})

        request_body = {
            "model": self.model,
            "messages": self.history,
            "stream": True,
            "stream_options": {"include_usage": True}
        }

        response = requests.post(
            self.base_url,
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
                logger.log(f"非法 JSON：{data}")
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
                logger.log(usage_msg)
                continue

            logger.log(f"收到未知 chunk：{chunk}")

        # ---------- 处理工具调用 ----------
        # 预编译正则表达式
        clean_pattern = re.compile(r'</?(out_text|thinking)>', flags=re.S)

        xml_pattern = re.compile(r'<(\w+)>.*?</\1>', flags=re.S)

        clean_content = clean_pattern.sub('', full_content)
        logger.log(clean_content)
        xml_blocks = [m.group(0) for m in xml_pattern.finditer(clean_content)]

        # 一次性执行所有工具，并把结果汇总
        tool_results = []
        for block in xml_blocks:
            try:
                logger.log(f"[DEBUG] 执行 XML: {repr(block)}")
                result = str(self.agent.run(block))
                tool_results.append(result)
            except Exception as e:
                tool_results.append(f"工具异常：{e}")

        if tool_results:
            # 把所有工具结果一次性给 AI，让它继续思考
            self.history.append({"role": "system",
                                 "content": "工具返回：\n" + "\n".join(tool_results)})
            full_content = self.conversation()  # 只再请求一次

        # 最终保存
        self.history.append({"role": "assistant", "content": full_content})

        # 只在这里判断是否结束
        if "<attempt_completion>" in full_content:
            logger.log("检测到 <attempt_completion>，会话结束")
            print("\n[系统] AI 已标记任务完成，程序退出。")
            exit(0)

        return full_content


class Agent:
    """XML 指令自动调用工具"""
    def __init__(self, llm: "LLMChat"):
        self.llm = llm
        self._tools = {
            name: getattr(self, name)
            for name in dir(self)
            if not name.startswith('_') and callable(getattr(self, name))
        }
    # ============================tools============================
    def execute_command(self,
                        command: str,
                        requires_approval: bool,
                        ) -> str:
        """
        在指定目录下执行命令，跨平台兼容。

        :param command:          要执行的 CLI 命令（字符串）。
        :param requires_approval: 布尔值，指示该命令是否需要用户批准才能执行。
        :param target_dir:        执行命令前切换的工作目录。
        :return:                  命令的标准输出与标准错误（合并后字符串）。
        """
        target_dir = self.conversations_folder
        if not os.path.isdir(target_dir):
            raise NotADirectoryError(f"目录不存在: {target_dir}")

        # 根据平台构造 shell 调用
        if platform.system() == "Windows":
            cmd = ["cmd", "/c", command]
        else:
            cmd = ["/bin/sh", "-c", command]

        # 需要审批时，向用户确认
        if requires_approval:
            ans = input(f"需要执行命令: {command}\n在目录: {target_dir}\n是否继续? [y/N] ").strip().lower()
            if ans != "y":
                return "用户取消执行"

        proc = subprocess.run(
            cmd,
            cwd=target_dir,
            capture_output=True,
            text=True
        )
        output = (proc.stdout + proc.stderr).strip()
        if proc.returncode != 0:
            raise RuntimeError(f"命令返回非零状态({proc.returncode})\n{output}")
        return output


    def read_file(self, path: str) -> str:
        logger.log(f"[DEBUG] read_file called with path={path}")
        file_suffix = "." + path.split(".")[-1]
        special_suffix = [
            '.asm', '.bash', '.bat', '.bib', '.c', '.cc', '.cfg', '.cls', '.cmd',
            '.conf', '.config', '.cpp', '.css', '.csv', '.cxx', '.diff', '.dockerfile',
            '.env', '.f', '.f03', '.f08', '.f90', '.f95', '.fish', '.for', '.go',
            '.h', '.hh', '.hlsl', '.hpp', '.htm', '.html', '.hxx', '.ini', '.java',
            '.jenkinsfile', '.js', '.json', '.jsx', '.jsp', '.kt', '.latex', '.less',
            '.log', '.lua', '.m', '.markdown', '.md', '.mm', '.mjs', '.pas', '.patch',
            '.php', '.pl', '.pm', '.properties', '.ps1', '.py', '.pyx', '.r', '.rb',
            '.rs', '.rst', '.s', '.sass', '.scala', '.scss', '.sh', '.sql', '.sty',
            '.sv', '.svh', '.swift', '.tab', '.tex', '.toml', '.ts', '.tsx', '.tsv',
            '.txt', '.v', '.vb', '.vhd', '.vhdl', '.xhtml', '.xml', '.yaml', '.yml',
            '.zsh'
        ]
        if not file_suffix in special_suffix:
            return "暂时无法为您处理文件"
        else:
            try:
                file_path = Path(self.llm.conversations_folder) / path
                logger.log(f"[DEBUG] full path={file_path.resolve()}")
                with open(file_path.resolve(), "r", encoding="utf-8") as f:
                    content = f.read()
                logger.log(f"[DEBUG] read_file success, len={len(content)}")
                return content
            except Exception as e:
                logger.log(f"[DEBUG] read_file exception: {e}")
                return f"读取失败: {e}"



    def write_to_file(self, path: str, content: str):
        logger.log(f"[read_file] 准备读取: {Path(self.llm.conversations_folder) / path}")
        file_suffix = "." + path.split(".")[-1]
        special_suffix = [
            '.asm', '.bash', '.bat', '.bib', '.c', '.cc', '.cfg', '.cls', '.cmd',
            '.conf', '.config', '.cpp', '.css', '.csv', '.cxx', '.diff', '.dockerfile',
            '.env', '.f', '.f03', '.f08', '.f90', '.f95', '.fish', '.for', '.go',
            '.h', '.hh', '.hlsl', '.hpp', '.htm', '.html', '.hxx', '.ini', '.java',
            '.jenkinsfile', '.js', '.json', '.jsx', '.jsp', '.kt', '.latex', '.less',
            '.log', '.lua', '.m', '.markdown', '.md', '.mm', '.mjs', '.pas', '.patch',
            '.php', '.pl', '.pm', '.properties', '.ps1', '.py', '.pyx', '.r', '.rb',
            '.rs', '.rst', '.s', '.sass', '.scala', '.scss', '.sh', '.sql', '.sty',
            '.sv', '.svh', '.swift', '.tab', '.tex', '.toml', '.ts', '.tsx', '.tsv',
            '.txt', '.v', '.vb', '.vhd', '.vhdl', '.xhtml', '.xml', '.yaml', '.yml',
            '.zsh'
        ]
        if not file_suffix in special_suffix:
            return "暂时无法为您处理文件"
        else:
            with open((Path(self.llm.conversations_folder) / path).resolve(), "w+", encoding="utf-8") as f:
                f.write(content)


    def replace_in_file(self, path: str, diff: str):
        """
        模拟 replace_in_file 的行为，根据 diff 中的 SEARCH/REPLACE 块修改文件。
        """
        # 读取原文件内容
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 解析 diff 中的 SEARCH/REPLACE 块
        pattern = re.compile(
            r'<<<<<<< SEARCH\n(.*?)\n=======\n(.*?)\n>>>>>>> REPLACE',
            re.DOTALL
        )

        # 替换每个匹配到的 SEARCH 块
        matches = pattern.findall(diff)
        for search, replace in matches:
            # 精确匹配（包括换行和缩进）
            if search in content:
                content = content.replace(search, replace, 1)
            else:
                raise ValueError("SEARCH 内容未找到，无法替换")

        # 写回文件
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)


    def search_files(self, path, regex, file_pattern=None):
        cmd = ["rg", "-n", regex, path]
        if file_pattern:
            cmd.extend(["-g", file_pattern])
        result = subprocess.run(cmd, capture_output=True, text=True)
        print(result.stdout)


    def list_files(self, path: str, recursive: bool = False) -> List[str]:
        """
        列出目录内容。
        :param path: 相对路径
        :param recursive: 是否递归
        :return: 相对路径字符串列表（文件/目录）
        """
        root = Path(path)
        if recursive:
            return [str(p.relative_to(root.parent)) for p in root.rglob('*')]
        else:
            return [str(p.relative_to(root.parent)) for p in root.iterdir()]


    def _scan_file(self, file: Path) -> Dict[str, List[str]]:
        """解析单个 Python 文件，返回顶层定义名称"""
        try:
            tree = ast.parse(file.read_text(encoding='utf-8'), filename=str(file))
        except Exception:
            return {}

        defs = {"classes": [], "functions": [], "methods": []}
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                defs["classes"].append(node.name)
            elif isinstance(node, ast.FunctionDef):
                defs["functions"].append(node.name)
        return defs


    def list_code_definition_names(self, path: str) -> Dict[str, Dict[str, List[str]]]:
        """
        扫描目录顶层 Python 文件，返回各文件的定义名称。
        :param path: 目录相对路径
        :return: {文件相对路径: {"classes": [..], "functions": [..]}}
        """
        root = Path(path)
        result = {}
        for py_file in root.glob("*.py"):
            result[str(py_file.relative_to(root.parent))] = self._scan_file(py_file)
        return result


    def search_files(self, path: str, regex: str, file_pattern: str = None) -> List[Dict]:
        """
        递归搜索目录，返回匹配行及其上下文。
        :param path: 目录相对路径
        :param regex: Rust 正则表达式字符串
        :param file_pattern: glob 过滤，如 "*.ts"
        :return: 列表，每项为 {"file": ..., "line": ..., "context": ...}
        """
        pattern = re.compile(regex)
        root = Path(path)
        matches = []

        def _iter_files():
            if file_pattern:
                return root.rglob(file_pattern)
            else:
                return (p for p in root.rglob('*') if p.is_file())

        for file in _iter_files():
            try:
                lines = file.read_text(encoding='utf-8').splitlines()
            except UnicodeDecodeError:
                continue  # 跳过二进制文件

            for idx, line in enumerate(lines, 1):
                if pattern.search(line):
                    context = "\n".join(
                        lines[max(0, idx - 2): idx + 1]
                    ).strip()
                    matches.append({
                        "file": str(file.relative_to(root.parent)),
                        "line": idx,
                        "context": context
                    })
        return matches

    def attempt_completion(self, result, command = None):
        print(result)
        if command:
            self.execute_command(command, False)
        sys.exit(0)

    # ===== 调度 =====
    def run(self, xml_cmd: str):
        """
        解析 XML 指令 -> 调用对应工具。
        支持：
            <read_file>
                <path>tools.py</path>
            </read_file>
        其中节点文本如果是 list/dict/数字会安全反序列化，
        否则按字符串处理。
        """
        def safe_eval(text: str):
            """把节点文本安全地反序列化成 Python 对象。"""
            text = text.strip()
            try:
                # 尝试解析为字面量（list / dict / int / float / bool / None）
                return ast.literal_eval(text)
            except (ValueError, SyntaxError):
                # 失败就原样返回字符串
                return text

        root = ET.fromstring(xml_cmd.strip())
        tool_name = root.tag

        if tool_name not in self._tools:
            raise ValueError(f"未知工具：{tool_name}")

        # 把子节点文本转换成参数字典
        kwargs = {child.tag: safe_eval(child.text) for child in root}

        # 校验参数与函数签名
        sig = inspect.signature(self._tools[tool_name])
        sig.bind(**kwargs)

        # 真正调用
        return self._tools[tool_name](**kwargs)


if __name__ == "__main__":
    llm_chat = LLMChat(os.getcwd())
    while True:
        user_input = input("\n[用户] ")
        if not user_input.strip():
            continue
        llm_chat.conversation_with_tool(user_input)