# AI Company - Multi-Agent Collaboration System Framework

AI Company is a modular multi-agent system framework based on large language models (LLMs) that enables the creation and management of multiple AI agents for collaborative task execution.

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-Apache_2.0-green.svg)](https://opensource.org/licenses/Apache-2.0)
[![uv](https://img.shields.io/badge/managed%20with-uv-5536ab.svg)](https://github.com/astral-sh/uv)

---

## Table of Contents / 目录

- [Core Features / 核心特性](#core-features--核心特性)
- [Architecture / 架构设计](#architecture--架构设计)
- [Quick Start / 快速开始](#quick-start--快速开始)
- [Usage Guide / 使用指南](#usage-guide--使用指南)
- [Communication Protocol / 通信协议](#communication-protocol--通信协议)
- [Complete Example / 完整示例](#complete-example--完整示例)
- [Project Structure / 项目结构](#project-structure--项目结构)
- [Limitations & Notes / 限制与注意事项](#limitations--notes--限制与注意事项)
- [License / 许可证](#license--许可证)

---

## Core Features / 核心特性

### Multi-Agent System / 多智能体系统

- Support for creating multiple AI agents with different roles and capabilities
- 支持创建多个具有不同角色和能力的 AI 智能体
- Agent management via dual-key (UUID + name) registration system
- 智能体通过 UUID 和名称双键注册系统进行管理
- Compatible with OpenAI API endpoints
- 支持 OpenAI 兼容的 API 端点

### Agent Communication / 智能体通信

- XML-tag-based inter-agent communication mechanism
- 基于 XML 标签的智能体间通信机制
- Support for dynamic agent discovery and collaboration
- 支持智能体动态发现和协作
- Built-in task completion reporting mechanism
- 内置任务完成报告机制

### Permission-Based Tool System / 权限工具系统

- Fine-grained tool permission control
- 细粒度的工具权限控制
- Support for global tools and agent-specific tools
- 支持全局工具和特定智能体工具
- Tool registration via decorator pattern
- Decorator 模式注册工具

### Comprehensive Monitoring / 完整监控

- Real-time streaming response processing
- 实时流式响应处理
- Automatic token usage statistics
- 自动 Token 使用量统计
- Structured logging based on Loguru
- 基于 Loguru 的结构化日志

---

## Architecture / 架构设计

```
AI Company
│
├── Dumplings/                    # Core Framework Package / 核心框架包
│   ├── __init__.py              # Module Exports / 模块导出
│   ├── Agent_Base_.py           # BaseAgent Abstract Class / BaseAgent 基类
│   ├── Agent_list.py            # Agent Registration System / 智能体注册系统
│   ├── agent_tool.py            # Tool Registry & Permissions / 工具注册与权限
│   └── mcp_bridge.py            # MCP Protocol Bridge / MCP 协议桥接
│
├── main.py                      # Application Entry Point / 应用入口
├── pyproject.toml               # Project Configuration / 项目配置
└── .env                         # Environment Variables / 环境变量
```

### Core Components / 核心组件

| Component / 组件 | Description / 说明 |
|------------------|-------------------|
| **BaseAgent** | Abstract base class for all agents, providing LLM communication, history management, and tool execution / 所有智能体的抽象基类，提供 LLM 通信、历史记录管理和工具执行 |
| **Agent Registration** | Dual-key (UUID + name) registration system using `@register_agent(uuid, name)` decorator / 双键（UUID + 名称）注册系统，使用 `@register_agent(uuid, name)` 装饰器 |
| **Tool Registry** | Permission-controlled tool registration system supporting `@tool_registry.register_tool()` / 权限控制的工具注册系统，支持 `@tool_registry.register_tool()` |
| **XML Parser** | XML tag parser based on BeautifulSoup / 基于 BeautifulSoup 的 XML 标签解析器 |
| **Communication Protocol** | XML tag specification defining inter-agent communication / 定义智能体间通信的 XML 标签规范 |

---

## Quick Start / 快速开始

### Requirements / 环境要求

- **Python >= 3.10**
- **uv** (Recommended package manager / 推荐的包管理器)

### Installation / 安装步骤

```bash
# Clone repository / 克隆项目
git clone https://github.com/Secret-Dumplings/AI_Company.git
cd AI_Company

# Install dependencies with uv / 使用 uv 安装依赖
uv sync

# Activate virtual environment (optional) / 激活虚拟环境 (可选)
uv shell
```

### Configure Environment / 配置环境变量

Create `.env` file in project root directory:

在项目根目录创建 `.env` 文件：

```env
API_KEY=your_llm_api_key_here
```

---

## Usage Guide / 使用指南

### 1. Creating an Agent / 创建智能体

Agents inherit from `BaseAgent` base class and are registered using the `@register_agent` decorator.

```python
import Dumplings
import os
import uuid

@Dumplings.register_agent(uuid.uuid4().hex, "my_agent")
class MyAgent(Dumplings.BaseAgent):
    """Agent role description / 智能体角色描述"""

    # System prompt / 系统提示词
    prompt = "You are a professional assistant / 你是一个专业的助手"

    # LLM API endpoint / LLM API 端点
    api_provider = "https://api.example.com/v1/chat/completions"

    # Model name / 模型名称
    model_name = "gpt-4o"

    # API key / API 密钥
    api_key = os.getenv("API_KEY")

    # Whether to support Function Calling / 是否支持 Function Calling
    fc_model = True

    def __init__(self):
        super().__init__()
```

### 2. Registering Tools / 注册工具

Tools are registered via the `@tool_registry.register_tool` decorator, controlling which agents can use them.

```python
@Dumplings.tool_registry.register_tool(
    allowed_agents=["my_agent", "other_agent"],  # List of agents allowed to use / 允许使用的智能体列表
    name="search_web",                           # Tool name / 工具名称
    description="Search internet information / 搜索互联网信息",  # Tool description / 工具描述
    parameters={                                 # Parameter definition (JSON Schema) / 参数定义（JSON Schema）
        "type": "object",
        "properties": {
            "query": {"type": "string", "description": "Search keywords / 搜索关键词"}
        },
        "required": ["query"]
    }
)
def search_web(xml: str = None) -> str:
    # Tool implementation logic / 工具实现逻辑
    # xml parameter contains XML-formatted tool call information / xml 参数包含 XML 格式的工具调用信息
    return "Search results... / 搜索结果..."
```

### 3. Tool Permission Explanation / 工具权限说明

- `allowed_agents` is `None` or empty list: Tool is available to all agents (global tool)
- `allowed_agents` 为 `None` 或空列表：该工具对所有智能体可用（全局工具）
- `allowed_agents` specifies agent name list: Only agents in the list can use this tool
- `allowed_agents` 指定智能体名称列表：只有列表中的智能体可以使用该工具
- Tool functions receive an `xml` parameter containing the raw XML tool call content
- 工具函数接收一个 `xml` 参数，包含原始的 XML 工具调用内容

### 4. Running the System / 运行系统

Run the main program:

运行主程序：

```bash
uv run main.py
```

### 5. Using Agents / 使用智能体

```python
import Dumplings
from Dumplings import agent_list

# Get agent by name / 通过名称获取智能体
agent = agent_list["my_agent"]

# Chat with agent (with tool support) / 与智能体对话（带工具支持）
agent.conversation_with_tool("Please help me complete a task / 请帮我完成某个任务")

# Or send message directly / 或者直接发送消息
response = agent.send_message("Hello / 你好")
```

---

## Communication Protocol / 通信协议

Inter-agent and agent-tool communication uses XML tags.

### Agent-to-Agent Communication / 智能体间通信

Agents can request help from other agents using the following XML tag:

```xml
<ask_for_help>
    <agent_id>Target agent UUID or name / 目标智能体UUID或名称</agent_id>
    <message>Request content / 请求内容</message>
</ask_for_help>
```

- `agent_id`: Target agent's UUID or registered name / 目标智能体的 UUID 或注册名称
- `message`: Message content to send to target agent / 要发送给目标智能体的消息内容

### Tool Invocation / 工具调用

Agents can call tools using the following format:

```xml
<tool_name>
    <param1>value1</param1>
    <param2>value2</param2>
</tool_name>
```

- Tag name must match the registered tool name / 标签名必须与注册的工具名称一致
- Child tag names correspond to tool parameter names / 子标签名称对应工具参数名
- Tool return value is automatically passed back to the agent / 工具的返回值会自动传递回智能体

### Task Completion / 任务完成

Agents can report task completion using the following tag:

```xml
<attempt_completion>
    <report_content>Task completion report content / 任务完成报告内容</report_content>
</attempt_completion>
```

- `report_content`: Summary report after task completion / 任务完成后的总结报告

### List Available Agents / 列出可用智能体

Agents can get a list of all available agents using:

```xml
<list_agents></list_agents>
```

Returns content containing UUIDs and names of all registered agents.

返回内容包含所有已注册智能体的 UUID 和名称。

---

## Complete Example / 完整示例

The following is a complete example showing how to create two agents and enable them to collaborate:

```python
import sys
from dotenv import load_dotenv
import os
import Dumplings
import uuid

load_dotenv()

# 1. Register tool - Get current time / 注册工具 - 获取当前时间
@Dumplings.tool_registry.register_tool(
    allowed_agents=["time_agent"],  # Only time_agent can use / 只有 time_agent 可以使用
    name="get_time",
    description="Get current time / 获取当前时间",
    parameters={
        "type": "object",
        "properties": {},
        "required": []
    }
)
def get_time(xml=None):
    """Tool function to get current time / 获取当前时间的工具函数"""
    from datetime import datetime
    return datetime.now().strftime("%H:%M:%S")

# 2. Create time agent / 创建时间智能体
@Dumplings.register_agent(uuid.uuid4().hex, "time_agent")
class TimeAgent(Dumplings.BaseAgent):
    """Time management agent / 时间管理智能体"""

    prompt = "You are a time management assistant, you can query the current time. You have a tool called get_time that you can call. / 你是一个时间管理助手，可以查询当前时间。你有一个工具叫 get_time 可以调用。"
    api_provider = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    model_name = "deepseek-v3.2"
    api_key = os.getenv("API_KEY")

    def __init__(self):
        super().__init__()

# 3. Create scheduler agent / 创建调度智能体
@Dumplings.register_agent(uuid.uuid4().hex, "scheduler_agent")
class SchedulerAgent(Dumplings.BaseAgent):
    """Scheduler agent that can request help from other agents / 调度智能体，可以请求其他智能体帮助"""

    prompt = "You are a task scheduler assistant. You can request help from other agents using the <ask_for_help> tag. / 你是一个任务调度助手。你可以通过 <ask_for_help> 标签请求其他智能体帮助。"
    api_provider = "https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions"
    model_name = "deepseek-v3.2"
    api_key = os.getenv("API_KEY")
    fc_model = True  # Enable Function Calling / 启用 Function Calling

    def __init__(self):
        super().__init__()

# 4. Run conversation / 运行对话
if __name__ == "__main__":
    # Get scheduler agent / 获取调度智能体
    scheduler = Dumplings.agent_list["scheduler_agent"]

    # Initiate conversation, request to query current time / 发起对话，请求查询当前时间
    scheduler.conversation_with_tool("Please help me query the current time / 请帮我查询当前时间")
```

### Execution Result / 运行结果

When running the above code:

1. `scheduler_agent` receives the user request
2. `scheduler_agent` may use the `<ask_for_help>` tag to request help from `time_agent`
3. `time_agent` receives the request and calls the `get_time` tool
4. `time_agent` returns the time result to `scheduler_agent`
5. `scheduler_agent` returns the final result to the user

当运行上述代码时：

1. `scheduler_agent` 会接收到用户请求
2. `scheduler_agent` 可能会使用 `<ask_for_help>` 标签请求 `time_agent` 的帮助
3. `time_agent` 接收到请求后，会调用 `get_time` 工具
4. `time_agent` 将时间结果返回给 `scheduler_agent`
5. `scheduler_agent` 将最终结果返回给用户

---

## Project Structure / 项目结构

```
AI_Company/
├── Dumplings/                  # Core Framework / 核心框架
│   ├── __init__.py            # Module Exports / 模块导出
│   ├── Agent_Base_.py         # BaseAgent Base Class / BaseAgent 基类
│   ├── Agent_list.py          # Agent Registration Management / 智能体注册管理
│   ├── agent_tool.py          # Tool System / 工具系统
│   └── mcp_bridge.py          # MCP Bridge / MCP 桥接
├── logs/                      # Runtime Logs / 运行日志
│   └── app.log                # Application Log / 应用日志
├── main.py                    # Main Program Entry / 主程序入口
├── pyproject.toml             # Project Configuration / 项目配置
├── README.md                  # Project Documentation / 项目文档
├── CLAUDE.md                  # Claude Code Configuration / Claude Code 配置
└── .env                       # Environment Variables (need to create manually) / 环境变量 (需手动创建)
```

### Core File Description / 核心文件说明

- `Dumplings/Agent_Base_.py`: BaseAgent abstract base class, parent class of all agents
- `Dumplings/Agent_Base_.py`: BaseAgent 抽象基类，所有智能体的父类
- `Dumplings/Agent_list.py`: Agent registration system, maintains global `agent_list` dictionary
- `Dumplings/Agent_list.py`: 智能体注册系统，维护全局 `agent_list` 字典
- `Dumplings/agent_tool.py`: Tool registration system, maintains tool permissions and execution logic
- `Dumplings/agent_tool.py`: 工具注册系统，维护工具权限和执行逻辑
- `Dumplings/mcp_bridge.py`: MCP (Model Context Protocol) protocol bridge
- `Dumplings/mcp_bridge.py`: MCP (Model Context Protocol) 协议桥接
- `main.py`: Application main entry file
- `main.py`: 应用主入口文件

---

## Limitations & Notes / 限制与注意事项

### Known Limitations / 已知限制

**Beta Version** - Features may change, stability not guaranteed

**Beta 版本** - 功能可能变更，稳定性不保证

- **Error Handling**: Limited error handling capability for complex tool chains
- **错误处理**: 复杂工具链的错误处理能力有限
- **Permission System**: Basic permission control, advanced permission features to be improved
- **权限系统**: 基础权限控制，高级权限功能待完善
- **API Compatibility**: Compatibility may vary across different LLM providers
- **API 兼容性**: 不同 LLM 提供商的兼容性可能有差异
- **Performance**: Performance under large-scale agent concurrency scenarios has not been fully tested
- **性能**: 大规模智能体并发场景下的性能未经过充分测试

### Recommendations / 使用建议

- It is recommended to use models that support Function Calling for better experience
- 建议使用支持 Function Calling 的模型以获得更好体验
- Tool functions should be idempotent and stateless
- 工具函数应保持幂等性和状态无关
- Inter-agent communication should be concise, avoiding circular dependencies
- 智能体间的通信应尽量简洁，避免循环依赖
- Tool chains and error handling should be thoroughly tested before production deployment
- 生产环境部署前应充分测试工具链和错误处理
- Agent `prompt` should clearly describe available tools and collaboration methods
- 智能体的 `prompt` 应明确说明其可用的工具和协作方式

---

## License / 许可证

This project is licensed under the Apache License 2.0.

本项目采用 Apache License 2.0 开源协议。

```
Copyright 2026 Secret-Dumplings

Licensed under the Apache License, Version 2.0 (the "License");
you may not use this file except in compliance with the License.
You may obtain a copy of the License at

    http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
```

---

<div align="center">

### AI Company - Building the Future of Collaborative AI / 共建协作 AI 的未来

Powered by Large Language Models

</div>