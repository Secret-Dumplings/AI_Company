# AI Company

AI Company 是一个基于大语言模型的多智能体系统框架，允许创建和管理多个AI智能体进行协作任务。

**EN:** AI Company is a multi-agent system framework based on large language models, enabling creation and management of multiple AI agents for collaborative tasks.

## 项目概述 / Project Overview

**中文:** 本项目实现了一个可扩展的AI智能体架构，支持：
- 创建多个具有不同角色和功能的AI智能体
- 智能体之间的通信与协作
- 基于XML标签的工具调用机制
- 与大语言模型API的集成（默认支持openai）

**EN:** This project implements an extensible AI agent architecture supporting:
- Creation of multiple AI agents with different roles and functions
- Communication and collaboration between agents
- XML tag-based tool invocation mechanism
- Integration with LLM APIs (default support for OpenAI-compatible)

## 🏗️ 技术架构 / Technical Architecture

### 核心组件 / Core Components

1. **BaseAgent** - 所有智能体的基类，提供与LLM通信的基础功能
   - Base class for all agents, providing core LLM communication functionality

2. **Agent注册系统** - 支持通过UUID和名称两种方式注册和访问智能体
   - Agent registration system supporting both UUID and name-based access

3. **工具系统** - 基于XML标签的工具调用机制
   - Tool system with XML tag-based invocation mechanism

4. **通信机制** - 智能体间的消息传递和协作
   - Communication mechanism for message passing and collaboration between agents

### 📁 主要文件 / Main Files

- `main.py` - 系统入口点，包含示例智能体的创建和使用
  - System entry point with example agent creation and usage
- `Agent/Agent_Base_.py` - BaseAgent类，提供核心功能
  - BaseAgent class providing core functionality
- `Agent/Agent_list.py` - 智能体注册和管理
  - Agent registration and management
- `Agent/agent_tool.py` - 工具函数实现和注册系统
  - Tool function implementation and registration system
- `Agent/__init__.py` - 模块初始化
  - Module initialization

### 文件结构 / File Structure
```
Agent/
  - __init__.py
  - Agent_Base_.py
  - Agent_list.py
  - agent_tool.py
```

## ⚙️ 安装与配置 / Installation & Configuration

### 环境要求 / Requirements

- Python >= 3.12
- 依赖包见 `pyproject.toml` / Dependencies in `pyproject.toml`

### 安装步骤 / Installation Steps

1. 克隆项目 / Clone project:
   ```bash
   git clone https://github.com/Secret-Dumplings/AI_Company.git
   cd AI_Company
   ```

2. 安装依赖 / Install dependencies:
   使用uv（自行安装）/ Using uv (install separately):
   ```bash
   uv sync
   ```

### 环境变量配置 / Environment Variables

在项目根目录创建 `.env` 文件并配置以下变量：
Create `.env` file in project root and configure:

```env
API_KEY=your_api_key_here
```

## 🚀 使用方法 / Usage

### 创建智能体 / Creating Agents

在 `main.py` 中定义新的智能体类：
Define new agent classes in `main.py`:

```python
import Dumplings
import uuid
import os

@Dumplings.register_agent(uuid.uuid4().hex, "agent_name")
class MyAgent(Dumplings.BaseAgent):
    prompt = "智能体的角色提示词 / Agent role prompt"
    api_provider = "API端点 / API endpoint"
    model_name = "模型名称 / Model name"
    api_key = os.getenv("API_KEY")

    def __init__(self):
        super().__init__()
```

### 注册工具 / Registering Tools

```python
@Dumplings.tool_registry.register_tool(
    allowed_agents=["agent_name"], 
    name="tool_name",
    description="工具描述 / Tool description"
)
def my_tool(xml: str) -> str:
    # 工具实现 / Tool implementation
    return "执行结果 / Execution result"
```

### 运行系统 / Running the System

```bash
uv run main.py
```

## 🤝 智能体通信 / Agent Communication

智能体可以通过 `<ask_for_help>` XML标签与其他智能体通信：
Agents can communicate using `<ask_for_help>` XML tags:

```xml
<ask_for_help>
    <agent_id>目标智能体ID / Target agent ID</agent_id>
    <message>消息内容 / Message content</message>
</ask_for_help>
```

### 工具调用 / Tool Invocation

```xml
<tool_name>
    <parameter1>value1</parameter1>
    <parameter2>value2</parameter2>
</tool_name>
```

### 任务完成 / Task Completion

```xml
<attempt_completion>
    <report_content>完成报告 / Completion report</report_content>
</attempt_completion>
```

## ✨ 项目特点 / Features

1. **模块化设计** - 易于扩展和维护
   - Modular design - Easy to extend and maintain

2. **多智能体协作** - 支持复杂的任务分解和协作
   - Multi-agent collaboration - Supports complex task decomposition and cooperation

3. **工具调用** - 通过XML标签灵活调用各种工具
   - Tool invocation - Flexible tool calling via XML tags

4. **流式响应** - 支持流式数据处理，实时显示结果
   - Streaming response - Real-time result display with stream processing

5. **用量统计** - 自动统计API调用的token用量
   - Usage statistics - Automatic token usage tracking for API calls

6. **权限控制** - 基于角色的工具访问权限管理
   - Permission control - Role-based tool access management

## ⚠️ Beta版本说明 / Beta Version Notes

**中文:** 这是beta版本，功能可能会变化，稳定性不能保证。
**EN:** This is a beta release. Features may change and stability is not guaranteed.

**已知限制 / Known Limitations:**
- 复杂工具链的错误处理有限
  - Limited error handling for complex tool chains
- 基础权限系统需要增强
  - Basic permission system needs enhancement
- 不同API提供商的兼容性可能不同
  - API compatibility may vary across providers

## 🤝 贡献 / Contribution

欢迎提交Issue和Pull Request来改进项目。
Welcome to submit Issues and Pull Requests to improve the project.

## 📄 许可证 / License

[Apache-2.0 license](https://github.com/Secret-Dumplings/AI_Company#Apache-2.0-1-ov-file)

---

*AI Company - 共建协作AI的未来，一次一个代理。*  
*AI Company - Building the future of collaborative AI, one agent at a time.*