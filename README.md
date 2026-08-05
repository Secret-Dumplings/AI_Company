# AI Company — 多智能体协作系统框架

> 一个基于 LLM 的模块化多智能体系统框架，让多个 AI Agent 协作完成任务。
>
> A modular multi-agent system framework based on LLMs that enables multiple AI agents to collaborate on tasks.

[![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-Apache_2.0-green.svg)](https://opensource.org/licenses/Apache-2.0)
[![uv](https://img.shields.io/badge/managed%20with-uv-5536ab.svg)](https://github.com/astral-sh/uv)

**作者 / Author**：[secret-tangyuan](https://github.com/secret-tangyuan) · [个人介绍 / Gravatar](https://gravatar.com/secrettangyuan)

---

## 目录 / Table of Contents

- [核心特性 / Core Features](#核心特性--core-features)
- [架构设计 / Architecture](#架构设计--architecture)
- [快速开始 / Quick Start](#快速开始--quick-start)
- [使用指南 / Usage Guide](#使用指南--usage-guide)
- [通信协议 / Communication Protocol](#通信协议--communication-protocol)
- [完整示例 / Complete Example](#完整示例--complete-example)
- [项目结构 / Project Structure](#项目结构--project-structure)
- [限制与注意事项 / Limitations & Notes](#限制与注意事项--limitations-notes)
- [许可证 / License](#许可证--license)

---

## 核心特性 / Core Features

### 多智能体系统 / Multi-Agent System

支持创建多个不同角色和能力的 AI Agent。

Support creating multiple AI agents with different roles and capabilities.

- Agent 通过 UUID 和名称双键注册系统管理（`agent_list[uuid]` 和 `agent_list[name]` 命中同一实例）。
  Agents are managed via a dual-key (UUID + name) registration system.
- 兼容 OpenAI 兼容的 API 端点（也支持 Anthropic / 自定义网关，详见子模块 [Tangyuan/docs/](../Tangyuan/docs/protocols.md)）。
  Compatible with OpenAI-compatible endpoints (also supports Anthropic / custom gateways, see submodule docs).

### 智能体通信 / Agent Communication

基于 XML 标签的智能体间通信机制，支持动态发现与协作。

XML-tag-based inter-agent communication with dynamic discovery and collaboration.

- 内置 `ask_for_help` / `list_agents` / `attempt_completion` / `reload` 四个协作工具（`BaseAgent` / `AnthropicAgent` 双协议一致）。
  Built-in collaboration tools, consistent across protocols.
- 也支持原生 Function Calling（XML 和 FC 两种调用模式并存）。
  Also supports native Function Calling (XML and FC coexisting).

### 权限工具系统 / Permission-Based Tool System

细粒度的工具权限控制，支持全局工具和 Agent 专属工具。

Fine-grained tool permission control, with both global and per-Agent tools.

- 用 `@tool_registry.register_tool(allowed_agents=[...])` 注册时显式指定可用 Agent 列表；`None` / `[]` 表示全局可用。
  Decorator registration with explicit `allowed_agents` list; `None` / `[]` = global.
- 工具函数接收 `xml` 参数（含原始 XML 工具调用内容，兼容两种调用模式）。
  Tool functions take an `xml` parameter (raw XML tool call, compatibility across call modes).

### 完整监控 / Comprehensive Monitoring

实时流式响应、自动 Token 使用量统计、Loguru 结构化日志。

Real-time streaming, auto token usage stats, structured logging via Loguru.

- `BaseAgent` / `AnthropicAgent` 双协议共用同一套 `pack(out)` 事件总线，覆写 `out` 即可劫持输出到 logger/UI/队列。
  Both protocols share one `pack(out)` event bus; override `out` to redirect output.

### 协议无关的 Agent 工厂 / Protocol-Independent Agent Factory（v0.4.2+）

写一份 `Agent` 类，靠 `protocol` 字段切 OpenAI / Anthropic / 自家网关。

Write one `Agent` class, switch providers via a single `protocol` field.

```python
@tangyuanAI.template_agent("writer", uuid="…", description="…")
class Writer(tangyuanAI.Agent):
    protocol     = "openai"        # 一行切协议（默认就是 openai）
    api_provider = "https://api.openai.com/v1"
    model_name   = "gpt-5"
    api_key      = os.getenv("API_KEY", "")
```
> 更多协议信息见子模块文档站 `https://docs.ai.secret-tangyuan.com/`。Full protocol docs at the submodule doc site.

---

## 架构设计 / Architecture

```
AI_Company
│
├── Tangyuan/                    # 核心框架包 / Core Framework Package
│   ├── __init__.py              # 模块导出 / Module Exports
│   ├── Agent_Base_.py           # BaseAgent 基类 / BaseAgent Base Class
│   ├── Agent_list.py            # Agent 注册系统 / Agent Registration
│   ├── agent_tool.py            # 工具注册与权限 / Tool Registry & Permissions
│   ├── anthropic_agent.py       # AnthropicAgent（旧实现兼容壳） / Compatibility Shim
│   └── mcp_bridge.py            # MCP 协议桥接 / MCP Protocol Bridge
│
├── main.py                      # 应用入口 / Application Entry Point
├── pyproject.toml               # 项目配置 / Project Configuration
└── .env                         # 环境变量 / Environment Variables
```

### 核心组件 / Core Components

| 组件 / Component | 说明 / Description |
|------------------|---------------------|
| **BaseAgent** | 所有 Agent 的抽象基类，提供 LLM 通信、历史管理、工具执行。Abstract base class for all agents: LLM I/O, history, tool execution. |
| **Agent 注册** | 双键（UUID + name）注册系统，用 `@template_agent` 装饰器（v0.3.0+ 模板池模式）。Dual-key registration via `@template_agent` decorator (template pool mode). |
| **Tool Registry** | 权限控制的工具注册系统：`@tool_registry.register_tool()` / Permission-controlled tool registration. |
| **XML Parser** | 基于 BeautifulSoup 的 XML 标签解析器。XML tag parser via BeautifulSoup. |
| **MCP Bridge** | MCP (Model Context Protocol) 协议桥接，支持 stdio MCP 服务器自动接入。Auto-bridge stdio MCP servers. |
| **协议无关 Agent** | `tangyuanAI.Agent`（带 `protocol` 字段）做工厂基类，自带 8 个内建工具。`tangyuanAI.Agent` factory with `protocol` field. |

---

## 快速开始 / Quick Start

### 环境要求 / Requirements

- **Python ≥ 3.10**
- **uv**（推荐包管理器 / Recommended package manager）

### 安装步骤 / Installation

```bash
# 克隆项目 / Clone
git clone https://github.com/secret-tangyuan/AI_Company.git
cd AI_Company

# 用 uv 安装依赖 / Install deps with uv
uv sync

# 激活虚拟环境（可选）/ Activate venv (optional)
uv shell
```

### 配置环境变量 / Configure Environment

在项目根目录创建 `.env`文件，配置 LLM API Key：

Create `.env` at the project root for LLM API keys:

```env
API_KEY=your_llm_api_key_here
```

> 详见子模块 `https://docs.ai.secret-tangyuan.com/` 的「快速开始」章节。
> See the submodule doc site "Quickstart" for full setup.

---

## 使用指南 / Usage Guide

### 1. 创建智能体 / Creating an Agent

Agent 继承 `BaseAgent`（或 `AnthropicAgent`，或用统一 `Agent` + `protocol` 字段），用 `@template_agent` 装饰器登记到模板池，再 `activate_template(...)` 实例化：

Agents inherit from `BaseAgent` (or `AnthropicAgent`, or use `Agent` + `protocol` field), register via `@template_agent` decorator, then activate with `activate_template()`:

```python
import os
import tangyuanAI
from tangyuanAI.Agent_list import activate_template

@tangyuanAI.template_agent(
    "my_agent",
    uuid=uuid.uuid4().hex,
    description="一句话说明这个 Agent 的用途",
)
class MyAgent(tangyuanAI.BaseAgent):
    """智能体角色描述 / Agent description"""

    prompt = "你是一个专业的助手"  # 系统提示词 / System prompt
    api_provider = "https://api.example.com/v1/chat/completions"  # LLM 端点
    model_name   = "gpt-4o"  # 模型名 / Model name
    api_key      = os.getenv("API_KEY")  # API 密钥
    fc_model     = True  # 是否启用 Function Calling

    def __init__(self):
        super().__init__()

activate_template("my_agent")  # 实例化 + 写入 agent_list
agent = tangyuanAI.agent_list["my_agent"]
```

> v0.3.0 起，旧版 `@register_agent(uuid, name, desc)` 装饰器已弃用，请用 `@template_agent` + 显式 `activate_template()`。
> `@register_agent(uuid, name, desc)` is deprecated since v0.3.0; use `@template_agent` + explicit `activate_template()`.

### 2. 注册工具 / Registering Tools

```python
@tangyuanAI.tool_registry.register_tool(
    allowed_agents=["my_agent", "other_agent"],  # 允许的 Agent 列表
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
    # xml 参数包含 XML 格式的工具调用内容（兼容两种调用模式）
    return "搜索结果..."
```

### 3. 工具权限说明 / Tool Permission Notes

- `allowed_agents = None` 或 `[]` → 工具对所有 Agent 可用（全局工具 / global tool）
- `allowed_agents = [...]` → 只有列表里的 Agent 能用（按 name 匹配，不是 uuid）
- 工具函数可接收 `xml` 参数，含原始 XML 工具调用内容

> **注意**：参数列表传的是 **Agent name**，**不是 uuid**。`tool_registry.check_permission` 内部会做 uuid→name 翻译。
> **Note**: pass Agent **name**, **not uuid**. `check_permission` internally translates uuid→name.

### 4. 运行系统 / Running the System

```bash
uv run main.py
```

### 5. 使用智能体 / Using Agents

```python
import tangyuanAI
from tangyuanAI import agent_list

# 通过名称取 Agent / by name
agent = agent_list["my_agent"]

# 带工具调用的对话（FC + XML 自动选择）
agent.conversation_with_tool("请帮我完成某个任务")

# 也可以直接发消息（不走工具调用）
response = agent.send_message("你好")
```

---

## 通信协议 / Communication Protocol

Agent ↔ Agent、Agent ↔ Tool 走 XML 标签（除非 `fc_model=True` 走原生 function calling）。

Inter-agent and Agent-Tool messages use XML tags (unless `fc_model=True` uses native function calling).

### 智能体间通信 / Agent-to-Agent

```xml
<ask_for_help>
  <agent_id>目标 Agent 的 UUID 或 name</agent_id>
  <message>请求内容</message>
</ask_for_help>
```

- `agent_id` — 目标 Agent 的 UUID 或 name
- `message` — 给目标 Agent 的消息

### 工具调用 / Tool Invocation

```xml
<tool_name>
  <param1>value1</param1>
  <param2>value2</param2>
</tool_name>
```

- 标签名 = 注册的工具名
- 子标签名 = 工具参数名
- 工具返回值自动回到 Agent

### 任务完成 / Task Completion

```xml
<attempt_completion>
  <report_content>总结报告内容</report_content>
</attempt_completion>
```

### 列出可用 Agent / List Available Agents

```xml
<list_agents></list_agents>
```

返回内容包含所有已注册 Agent 的 UUID 和名称。

---

## 协议简单性 —— 1 行 = 100 行 / Protocol simplicity — 1 line = 100 lines

两个 Agent 通信需要一套协议。Google 的 A2A（Agent-to-Agent）是公开参考：JSON-RPC 2.0 over HTTP + SSE 流式任务 + agent card 发现 + 状态机（`submitted → working → input-required → completed/failed/canceled`）。

Agent-to-agent communication needs a protocol. Google's A2A is one open reference: JSON-RPC 2.0 over HTTP, SSE-streamed tasks, agent card discovery, plus a state machine (`submitted → working → input-required → completed/failed/canceled`).

如果从零写一个 A2A 客户端调远端 Agent，代码至少要包含：

If you wrote an A2A client from scratch, it'd at least contain:

```python
import httpx, json, asyncio, uuid

REMOTE_AGENT_URL = "http://remote-agent.example.com"

# 1. 发现：通过 well-known 端点拉 agent card（skills / auth schemes / transport 偏好）
async def call_remote_agent(user_text: str) -> str:
    async with httpx.AsyncClient() as client:
        card = (await client.get(f"{REMOTE_AGENT_URL}/.well-known/agent.json")).json()

        # 2. 构造 JSON-RPC 2.0 + SendMessageRequest
        req = {
            "jsonrpc": "2.0", "id": 1,
            "method": "tasks/sendSubscribe",
            "params": {
                "id": str(uuid.uuid4()),
                "sessionId": "session-1",
                "message": {
                    "role": "user",
                    "parts": [{"type": "text", "text": user_text}],
                },
                "acceptedOutputModes": ["text/plain"],
            },
        }

        # 3. SSE 流订阅 + 状态机分支
        final_state, final_text = None, ""
        async with client.stream(
            "POST", f"{REMOTE_AGENT_URL}/a2a/v1/tasks/sendSubscribe",
            json=req,
            headers={
                "Authorization": f"Bearer {API_KEY}",
                "X-A2A-Headers": json.dumps({"X-Locale": "zh-CN"}),
            },
        ) as r:
            async for line in r.aiter_lines():
                if not line.startswith("data:"):
                    continue
                event = json.loads(line[5:])
                if "status" in event:
                    state = event["status"]["state"]
                    if state == "input-required":
                        # 用户侧弹窗补信息 → SendMessage 续推
                        ...
                    elif state in ("completed", "failed", "canceled"):
                        final_state = state
                if "artifact" in event:
                    for part in event["artifact"].get("parts", []):
                        if part.get("type") == "text":
                            final_text += part["text"]
                if final_state:
                    break
        return final_text if final_state == "completed" else ""

# 4. 错误处理：远端抛 SkillNotFound / ToolError / 网络中断 / SSE 断流 → 自己重试 + 重连
```

> 50+ 行：发现 + JSON-RPC 构造 + SSE 流解析 + 状态机分支 + 鉴权头 + 错误重试 + 重连。

工具 schema 也要手写：Each tool's `inputSchema` written by hand:

```python
# A2A skill 注册：手写整套 JSON Schema
skill_def = {
    "name": "search_web",
    "description": "搜索互联网信息",
    "inputSchema": {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "type": "object",
        "properties": {
            "query": {
                "type": "string",
                "description": "搜索关键词",
                "minLength": 1,
                "maxLength": 200,
            },
        },
        "required": ["query"],
        "additionalProperties": False,
    },
}
agent_card["skills"].append(skill_def)
```

用 tangyuanAI：用 Python 函数签名 + 类型注解，schema 自动推。用 `tangyuanAI`：

```python
from tangyuanAI import builtin_tool

@builtin_tool(
    description="搜索互联网信息",
    params={"query": "搜索关键词"},   # 描述可覆写；类型/必填从签名推
)
def search_web(query: str) -> str:        # type=string / required=query 都自动
    return "搜索结果..."
```

> 一个 Python 函数 = 一份 JSON Schema。无需重复声明字段名 / 类型 / required / 描述。

tangyuanAI 表达"调度一下 writer_agent 帮我查北京天气"——只一行：

tangyuanAI expressing "ask writer_agent to look up Beijing weather" — one line:

```python
result = tangyuanAI.agent_list["scheduling_agent"].ask_for_help(
    agent_id="writer_agent",
    message="请帮我查一下北京今天天气",
)
# .ask_for_help 里自动：cycle detection / depth limit / worker pool / XML↔FC / 流式装配
```

> 一个调用：循环检测、深度限制、worker 池、协议兼容（XML/FC）、流式装配都内建。

框架的设计取舍：把协议描述（人可读，比如"用 `<ask_for_help>` 请其他 Agent"）和工具描述（机器可调）合并成同一套接口；函数签名同时是工具 schema。LLM 看 prompt 就知道怎么调其他 Agent，不需要单独学 A2A 协议，也不需要手写 JSON Schema。

The framework's design choice: merge protocol descriptions (human-readable, e.g. "use `<ask_for_help>` to call other agents") and tool descriptions (machine-callable) into one surface — and the function signature is also the tool schema. The LLM reads the prompt and knows how to call other agents — no separate A2A protocol to learn, no JSON Schema to hand-write.

---

## 完整示例 / Complete Example

下面的例子演示两个 Agent 协作：

The example below shows two agents collaborating:

```python
import sys
from dotenv import load_dotenv
import os
import uuid
import tangyuanAI
from tangyuanAI.Agent_list import activate_template

load_dotenv()

# 1. 注册工具：获取当前时间
@tangyuanAI.tool_registry.register_tool(
    allowed_agents=["time_agent"],
    name="get_time",
    description="获取当前时间",
    parameters={
        "type": "object",
        "properties": {},
        "required": []
    }
)
def get_time(xml=None):
    from datetime import datetime
    return datetime.now().strftime("%H:%M:%S")

# 2. 创建时间 Agent
@tangyuanAI.template_agent(
    "time_agent",
    uuid=uuid.uuid4().hex,
    description="提供当前时间查询服务",
)
class TimeAgent(tangyuanAI.BaseAgent):
    """时间管理 Agent"""
    prompt = (
        "你是时间管理助手，可以查询当前时间，"
        "调用 get_time 工具返回格式 HH:MM:SS"
    )
    api_provider = os.getenv("API_BASE", "https://api.example.com/v1")
    model_name = os.getenv("MODEL", "gpt-4o")
    api_key = os.getenv("API_KEY")
    fc_model = True

    def __init__(self):
        super().__init__()

# 3. 创建调度 Agent
@tangyuanAI.template_agent(
    "scheduler_agent",
    uuid=uuid.uuid4().hex,
    description="调度 Agent：可调用 ask_for_help 请其他 Agent 协作",
)
class SchedulerAgent(tangyuanAI.BaseAgent):
    """调度 Agent：可请求其他 Agent 协助"""
    prompt = (
        "你是任务调度助手。"
        "需要时间查询时，用 <ask_for_help> 标签请 time_agent 帮忙"
    )
    api_provider = os.getenv("API_BASE", "https://api.example.com/v1")
    model_name = os.getenv("MODEL", "gpt-4o")
    api_key = os.getenv("API_KEY")
    fc_model = True

    def __init__(self):
        super().__init__()

# 4. 激活模板 + 跑对话
if __name__ == "__main__":
    activate_template("time_agent")
    activate_template("scheduler_agent")

    scheduler = tangyuanAI.agent_list["scheduler_agent"]
    scheduler.conversation_with_tool("请帮我查询当前时间")
```

### 运行过程 / What Happens When Running

1. `scheduler_agent` 收到用户请求 — receives user request
2. `scheduler_agent` 用 `<ask_for_help>` 标签请 `time_agent` 帮忙 — uses `<ask_for_help>` tag to ask `time_agent`
3. `time_agent` 调用 `get_time` 工具 — `time_agent` invokes `get_time` tool
4. `time_agent` 把时间结果返回给 `scheduler_agent` — returns the time to `scheduler_agent`
5. `scheduler_agent` 把最终结果返回给用户 — returns final answer to user

---

## 项目结构 / Project Structure

```
AI_Company/
├── Tangyuan/                  # 核心框架 / Core Framework (submodule)
│   ├── __init__.py            # 模块导出 / Module exports
│   ├── Agent_Base_.py         # BaseAgent 基类 / BaseAgent class
│   ├── Agent_list.py          # Agent 注册管理 / Agent registration
│   ├── agent_tool.py          # 工具系统 / Tool system
│   ├── anthropic_agent.py     # AnthropicAgent（兼容壳）/ Compatibility shim
│   └── mcp_bridge.py          # MCP 协议桥接 / MCP bridge
├── logs/                      # 运行日志 / Runtime logs
│   └── app.log                # 应用日志 / Application log
├── main.py                    # 主程序入口 / Main entry
├── pyproject.toml             # 项目配置 / Project config
├── README.md                  # 项目文档 / Project doc
└── .env                       # 环境变量 / Env vars
```

### 核心文件说明 / Key Files

- `Tangyuan/Agent_Base_.py` — `BaseAgent` 抽象基类，所有 Agent 的父类。Abstract base class.
- `Tangyuan/Agent_list.py` — Agent 注册系统，维持全局 `agent_list`。Agent registration system.
- `Tangyuan/agent_tool.py` — 工具注册系统，权限 + 执行。Tool system with permission.
- `Tangyuan/mcp_bridge.py` — MCP 协议桥接。MCP protocol bridge.
- `main.py` — 应用主入口。Main entry.

---

## 限制与注意事项 / Limitations & Notes

### 已知限制 / Known Limitations

当前为 **Beta** 阶段——功能可能变更，稳定性不保证。

Currently **Beta** — features may change, stability not guaranteed.

- **错误处理**：复杂工具链的错误处理能力有限。Limited for complex tool chains.
- **权限系统**：基础权限控制，高级权限待完善。Basic permission; advanced features pending.
- **API 兼容性**：不同 LLM 提供商的兼容性可能有差异。May vary across LLM providers.
- **性能**：大规模 Agent 并发场景下的性能未充分压测。Not fully stress-tested.

### 使用建议 / Recommendations

- 用支持 Function Calling 的模型体验更好。Prefer FC-capable models.
- 工具函数保持幂等且状态无关。Tool functions: idempotent & stateless.
- 智能体间通信保持简洁，避免循环依赖。Keep agent-to-agent messages concise; avoid cycles.
- 生产部署前充分测试工具链与错误处理。Stress-test tool chains and error handling before prod.
- Agent `prompt` 应明确说明可用工具和协作方式。Describe available tools and collaboration in `prompt`.

---

## 许可证 / License

本项目采用 Apache License 2.0 开源协议。

This project is licensed under Apache License 2.0.

```
Copyright 2026 secret-tangyuan

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

**共建协作 AI 的未来 · Building the future of collaborative AI**