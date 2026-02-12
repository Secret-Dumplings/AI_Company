# 如何开发一个 Agent

本文档详细介绍如何在 AI_Company 框架中开发和部署自定义 Agent。

---

## 目录

- [快速入门](#快速入门)
- [Agent 基础知识](#agent-基础知识)
- [创建 Agent](#创建-agent)
- [注册工具](#注册工具)
- [Agent 间通信](#agent-间通信)
- [MCP 工具集成](#mcp-工具集成)
- [完整示例](#完整示例)
- [调试与测试](#调试与测试)
- [最佳实践](#最佳实践)

---

## 快速入门

### 第一个 Agent

```python
import Dumplings
import os
import uuid

@Dumplings.register_agent(uuid.uuid4().hex, "my_first_agent")
class MyFirstAgent(Dumplings.BaseAgent):
    """我的第一个智能体"""

    prompt = "你是一个有用的助手。"
    api_provider = "https://api.example.com/v1/chat/completions"
    model_name = "gpt-4o"
    api_key = os.getenv("API_KEY")

    def __init__(self):
        super().__init__()
```

---

## Agent 基础知识

### BaseAgent 核心属性

每个 Agent 必须继承 `BaseAgent` 并实现以下必要属性：

| 属性 | 类型 | 说明 |
|------|------|------|
| `prompt` | str | 系统提示词，描述 Agent 的角色和能力 |
| `api_provider` | str | LLM API 端点地址 |
| `model_name` | str | 使用的模型名称 |
| `api_key` | str | API 密钥 |
| `fc_model` | bool | 是否启用 Function Calling (可选，默认 False) |

### Agent 注册机制

Agent 通过装饰器注册到全局 `agent_list`：

```python
@Dumplings.register_agent(uuid, name)
```

- **uuid**: 唯一标识符，推荐使用 `uuid.uuid4().hex`
- **name**: 可读的名称，用于人类识别

注册后，Agent 可以通过 UUID 或名称访问：
```python
agent = Dumplings.agent_list["my_agent"]  # 通过名称
agent = Dumplings.agent_list["uuid"]       # 通过 UUID
```

---

## 创建 Agent

### 基础模板

```python
import Dumplings
import os
import uuid

@Dumplings.register_agent(uuid.uuid4().hex, "agent_name")
class MyAgent(Dumplings.BaseAgent):
    """Agent 描述"""

    # 1. 系统提示词
    prompt = """
你是一个专业的 [角色描述]。

你可以使用以下工具：
- [工具1]: [描述]
- [工具2]: [描述]

你的 UUID 是 {self.uuid}
"""

    # 2. API 配置
    api_provider = "https://api.example.com/v1/chat/completions"
    model_name = "gpt-4o"
    api_key = os.getenv("API_KEY")

    # 3. 是否启用 Function Calling
    fc_model = True

    # 4. 初始化
    def __init__(self):
        super().__init__()
```

### 带自定义属性的 Agent

```python
@Dumplings.register_agent(uuid.uuid4().hex, "special_agent")
class SpecialAgent(Dumplings.BaseAgent):
    prompt = "你是一个特殊的智能体。"
    api_provider = "https://api.example.com/v1/chat/completions"
    model_name = "gpt-4o"
    api_key = os.getenv("API_KEY")

    # 自定义属性
    custom_config = {"max_attempts": 3, "timeout": 30}

    def __init__(self):
        super().__init__()
        self.attempts = 0

    # 自定义方法
    def custom_method(self):
        return f"当前尝试次数: {self.attempts}"
```

---

## 注册工具

### 工具装饰器参数

```python
@Dumplings.tool_registry.register_tool(
    allowed_agents=None,      # 允许使用的 Agent 列表 (None=全部)
    name="tool_name",         # 工具名称
    description="工具描述",    # 工具描述
    parameters={              # 参数定义 (JSON Schema)
        "type": "object",
        "properties": {
            "param1": {"type": "string", "description": "参数1描述"},
            "param2": {"type": "number", "description": "参数2描述"}
        },
        "required": ["param1"]
    }
)
```

### XML 模式工具 (次要支持，请使用function calling)

```python
@Dumplings.tool_registry.register_tool(
    allowed_agents=["my_agent"],
    name="search_web",
    description="搜索互联网信息",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "搜索关键词"}
        },
        "required": ["query"]
    }
)
def search_web(xml: str = None) -> str:
    """
    XML 模式工具函数

    Args:
        xml: XML 格式的工具调用信息，例如:
            <search_web><query>关键词</query></search_web>

    Returns:
        str: 工具执行结果
    """
    from bs4 import BeautifulSoup

    # 解析 XML
    soup = BeautifulSoup(xml, "xml")
    query = soup.find("query").text.strip()

    # 执行搜索逻辑
    result = f"搜索结果: {query}"

    return result
```

### Function Calling 模式工具

```python
@Dumplings.tool_registry.register_tool(
    allowed_agents=["my_agent"],
    name="calculate",
    description="执行数学计算",
    parameters={
        "type": "object",
        "properties": {
            "expression": {"type": "string", "description": "数学表达式"}
        },
        "required": ["expression"]
    }
)
def calculate(**kwargs) -> str:
    """
    Function Calling 模式工具

    Args:
        **kwargs: 工具参数，例如 {"expression": "2+2"}

    Returns:
        str: 计算结果
    """
    expression = kwargs.get("expression", "")
    try:
        result = eval(expression)
        return f"计算结果: {result}"
    except Exception as e:
        return f"计算错误: {e}"
```

### 工具权限控制

```python
# 全局工具 (所有 Agent 可用)
@Dumplings.tool_registry.register_tool(
    allowed_agents=None,
    name="log_event",
    description="记录事件"
)
def log_event(**kwargs):
    # 所有 Agent 都可以调用
    pass

# 限制特定 Agent 使用
@Dumplings.tool_registry.register_tool(
    allowed_agents=["agent1", "agent2"],
    name="admin_tool",
    description="管理员工具"
)
def admin_tool(**kwargs):
    # 只有 agent1 和 agent2 可以调用
    pass
```

---

## Agent 间通信

### 内置通信工具

Agent 自动拥有以下内置通信工具：

| 工具名 | 描述 | 参数 |
|--------|------|------|
| `ask_for_help` | 请求其他 Agent 帮助 | `agent_id`, `message` |
| `list_agents` | 列出所有可用 Agent | 无 |
| `attempt_completion` | 标记任务完成 | `report_content` (可选) |

### XML 模式通信 (建议不要使用)

```xml
<!-- 请求其他 Agent 帮助 -->
<ask_for_help>
    <agent_id>target_agent_uuid_or_name</agent_id>
    <message>请帮我完成这个任务</message>
</ask_for_help>

<!-- 列出所有 Agent -->
<list_agents></list_agents>

<!-- 标记任务完成 -->
<attempt_completion>
    <report_content>任务已完成，结果是...</report_content>
</attempt_completion>
```

### Function Calling 模式通信

```python
# 当 Agent 启用 fc_model=True 时，模型会自动调用这些函数
# 不需要手动编写调用代码
```

### 示例：Agent 协作

```python
@Dumplings.register_agent(uuid.uuid4().hex, "scheduler_agent")
class SchedulerAgent(Dumplings.BaseAgent):
    prompt = """
你是一个任务调度助手。你可以通过 <ask_for_help> 请求其他 Agent 帮助。

可用的工具：
- ask_for_help: agent_id(目标Agent的UUID或名称), message(请求内容)
"""
    api_provider = "https://api.example.com/v1/chat/completions"
    model_name = "gpt-4o"
    api_key = os.getenv("API_KEY")
    fc_model = True  # 启用 Function Calling

@Dumplings.register_agent(uuid.uuid4().hex, "data_agent")
class DataAgent(Dumplings.BaseAgent):
    prompt = "你是一个数据分析助手。"
    api_provider = "https://api.example.com/v1/chat/completions"
    model_name = "gpt-4o"
    api_key = os.getenv("API_KEY")

# 使用
scheduler = Dumplings.agent_list["scheduler_agent"]
scheduler.conversation_with_tool("请让 data_agent 帮我分析数据")
```

---

## MCP 工具集成

### MCP 服务器结构

MCP (Model Context Protocol) 工具位于 `Dumplings/mcp/` 目录下：

```
Dumplings/mcp/
├── weather_mcp/
│   └── weather_server.py  # 天气工具示例
└── [your_tool_name]/
    └── [your_server].py
```

### 注册 MCP 工具

```python
from Dumplings.mcp_bridge import register_mcp_tools

# 注册 MCP 服务器
register_mcp_tools("Dumplings/mcp/weather_mcp/weather_server.py")
```

### 创建 MCP 工具服务器

参考 `Dumplings/mcp/weather_mcp/weather_server.py` 示例：

```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MCP 工具服务器模板
"""

from mcp.server import Server
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

# 1. 创建服务器实例
server = Server("your-tool-server")

# 2. 定义工具列表
@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="your_tool_name",
            description="工具描述",
            inputSchema={
                "type": "object",
                "properties": {
                    "param1": {"type": "string", "description": "参数1"}
                },
                "required": ["param1"]
            }
        )
    ]

# 3. 处理工具调用
@server.call_tool()
async def handle_call_tool(
    name: str,
    arguments: dict | None
) -> list[types.TextContent]:
    if name == "your_tool_name":
        param1 = arguments.get("param1", "default")

        # 执行工具逻辑
        result = f"处理结果: {param1}"

        return [
            types.TextContent(type="text", text=result)
        ]

    raise ValueError(f"未知工具: {name}")

# 4. 启动服务器
async def main():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="your-tool-server",
                server_version="1.0.0"
            )
        )

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

---

## 完整示例

### 场景：时间管理助手

```python
import sys
from dotenv import load_dotenv
import os
import Dumplings
import uuid

load_dotenv()

# ============ 步骤1: 注册工具 ============

@Dumplings.tool_registry.register_tool(
    allowed_agents=["time_agent"],
    name="get_current_time",
    description="获取当前时间",
    parameters={
        "type": "object",
        "properties": {},
        "required": []
    }
)
def get_current_time(xml=None):
    """获取当前时间的工具"""
    from datetime import datetime
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@Dumplings.tool_registry.register_tool(
    allowed_agents=None,  # 全局工具
    name="search_info",
    description="搜索互联网信息",
    parameters={
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "搜索关键词"}
        },
        "required": ["query"]
    }
)
def search_info(**kwargs):
    """搜索工具 (伪实现)"""
    query = kwargs.get("query", "")
    return f"搜索结果: {query} - 这是一个示例结果"


# ============ 步骤2: 创建时间管理 Agent ============

@Dumplings.register_agent(uuid.uuid4().hex, "time_agent")
class TimeAgent(Dumplings.BaseAgent):
    """
    时间管理智能体
    - 可以查询当前时间
    - 可以通过 ask_for_help 请求其他 Agent 帮助
    """

    prompt = """
你是一个时间管理助手。你可以：
1. 使用 get_current_time 工具查询当前时间
2. 使用 <ask_for_help> 请求其他 Agent 帮助

你的 UUID 是 {self.uuid}
"""

    api_provider = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    model_name = "deepseek-v3.2"
    api_key = os.getenv("API_KEY")

    def __init__(self):
        super().__init__()


# ============ 步骤3: 创建任务调度 Agent ============

@Dumplings.register_agent(uuid.uuid4().hex, "scheduler_agent")
class SchedulerAgent(Dumplings.BaseAgent):
    """
    任务调度智能体
    - 可以搜索信息
    - 可以请求 time_agent 帮助
    - 支持 Function Calling
    """

    prompt = """
你是一个任务调度助手。你可以：
1. 使用 search_info 工具搜索信息
2. 使用 ask_for_help 请求 time_agent 帮助 (UUID: {time_agent_uuid})
3. 使用 attempt_completion 标记任务完成

可用的工具：
- search_info(query: str): 搜索互联网信息
- ask_for_help(agent_id: str, message: str): 请求其他 Agent 帮助
- list_agents(): 列出所有可用 Agent
- attempt_completion(report_content: str): 标记任务完成
"""

    api_provider = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    model_name = "deepseek-v3.2"
    api_key = os.getenv("API_KEY")
    fc_model = True  # 启用 Function Calling

    def __init__(self):
        super().__init__()


# ============ 步骤4: 运行对话 ============

if __name__ == "__main__":
    print("=" * 50)
    print("AI Company - 多智能体协作示例")
    print("=" * 50)

    # 获取调度智能体
    scheduler = Dumplings.agent_list["scheduler_agent"]

    # 发起对话
    print("\n[用户] 请帮我查询现在的时间，并搜索一下今天有什么新闻")
    print("\n[系统] 正在处理...\n")

    response = scheduler.conversation_with_tool(
        "请帮我查询现在的时间，并搜索一下今天有什么新闻"
    )

    print("\n\n[系统] 任务完成")
```

### 运行结果

```
==================================================
AI Company - 多智能体协作示例
==================================================

[用户] 请帮我查询现在的时间，并搜索一下今天有什么新闻

[系统] 正在处理...

[调度助手] 我需要查询当前时间并搜索新闻。让我先请求时间助手的帮助。

调用工具: ask_for_help
参数: {'agent_id': 'time_agent', 'message': '请帮我查询当前时间'}

[时间助手] 当前时间是 2026-02-12 14:30:00

[调度助手] 现在让我搜索今天的新闻。

调用工具: search_info
参数: {'query': '今天新闻'}

搜索结果: 今天新闻 - 这是一个示例结果

[调度助手] 已完成任务。当前时间是 2026-02-12 14:30:00，今天的新闻有...

[系统] 任务完成
```

---

## 调试与测试

### 1. 启用详细日志

```bash
# 设置日志级别为 TRACE
export LOGURU_LEVEL=TRACE
python main.py
```

日志文件位置: `logs/app.log`

### 2. 单独测试 Agent

```python
# 测试单个 Agent
agent = Dumplings.agent_list["my_agent"]

# 测试对话
response = agent.conversation_with_tool("你好")
print(response)

# 查看历史记录
print(agent.history)
```

### 3. 测试工具

```python
# 直接调用工具函数
result = get_current_time()
print(result)
```

### 4. 检查可用工具

```python
# 查看所有已注册工具
tools = Dumplings.tool_registry.list_tools()
print(tools)

# 查看特定 Agent 可用的工具
agent_tools = Dumplings.tool_registry.get_all_tools_info(agent_uuid)
print(agent_tools)
```

---

## 最佳实践

### 1. Prompt 设计

```python
# ❌ 不好的示例
prompt = "你是一个助手"

# ✅ 好的示例
prompt = """
你是一个专业的 [角色] 助手。

## 能力
- 能力1: 描述
- 能力2: 描述

## 可用工具
- tool1: 用途和参数说明
- tool2: 用途和参数说明

## 工作流程
1. 步骤1
2. 步骤2

## 输出格式
[说明输出格式]

你的 UUID 是 {self.uuid}
"""
```

### 2. 工具设计原则

- **幂等性**: 多次调用应该产生相同结果
- **状态无关**: 不依赖外部状态
- **错误处理**: 友好的错误提示
- **参数验证**: 检查必要参数

```python
@Dumplings.tool_registry.register_tool(
    allowed_agents=["my_agent"],
    name="safe_tool",
    description="安全的工具示例",
    parameters={
        "type": "object",
        "properties": {
            "data": {"type": "string", "description": "数据"}
        },
        "required": ["data"]
    }
)
def safe_tool(**kwargs):
    # 1. 验证参数
    if "data" not in kwargs:
        return "错误: 缺少必要参数 'data'"

    data = kwargs["data"]

    # 2. 执行逻辑
    try:
        # ... 处理逻辑
        result = f"处理成功: {data}"
        return result
    except Exception as e:
        return f"处理失败: {str(e)}"
```

### 3. Agent 协作设计

- **职责单一**: 每个 Agent 专注于特定任务
- **明确通信**: 使用清晰的 agent_id 和 message
- **避免循环依赖**: 防止 Agent 间无限调用

```python
# ✅ 好的协作设计
# Scheduler Agent -> Time Agent
# Scheduler Agent -> Search Agent

# ❌ 避免循环依赖
# Agent A -> Agent B
# Agent B -> Agent A  (可能导致死循环)
```

### 4. 性能优化

- **减少 API 调用**: 合并多个工具调用
- **缓存结果**: 对重复请求使用缓存
- **流式响应**: 使用流式输出提升用户体验

---

## 常见问题

### Q1: Agent 无法找到工具？

**检查**:
1. 工具是否正确注册
2. `allowed_agents` 是否包含当前 Agent
3. Prompt 中是否说明了可用工具

### Q2: Agent 间通信失败？

**检查**:
1. agent_id 是否正确 (UUID 或名称)
2. 目标 Agent 是否已注册
3. 提示词中是否说明了通信方式

### Q3: 如何选择 XML 模式还是 Function Calling？

**建议**:
- 支持 Function Calling 的模型: 使用 `fc_model = True`
- 不支持的模型: 使用 XML 模式 (默认)

### Q4: 如何调试 Agent 的思考过程？

**方法**:
1. 查看 `logs/app.log` 日志
2. 设置 `LOGURU_LEVEL=TRACE` 显示详细日志
3. 在工具函数中添加 print 调试信息

---

## 更多资源

- [README.md](README.md) - 项目概述和完整示例
- [CLAUDE.md](CLAUDE.md) - 开发环境配置
- [Dumplings/Agent_Base_.py](Dumplings/Agent_Base_.py) - BaseAgent 源码
- [Dumplings/agent_tool.py](Dumplings/agent_tool.py) - 工具系统源码

---