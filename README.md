# AI Company

AI Company 是一个基于大语言模型的多智能体系统框架，允许创建和管理多个AI智能体进行协作任务。

## 项目概述

本项目实现了一个可扩展的AI智能体架构，支持：
- 创建多个具有不同角色和功能的AI智能体
- 智能体之间的通信与协作
- 基于XML标签的工具调用机制
- 与大语言模型API的集成（默认支持openai）

## 技术架构

### 核心组件

1. **BaseAgent** - 所有智能体的基类，提供与LLM通信的基础功能
2. **Agent注册系统** - 支持通过UUID和名称两种方式注册和访问智能体
3. **工具系统** - 基于XML标签的工具调用机制
4. **通信机制** - 智能体间的消息传递和协作

### 主要文件

- `main.py` - 系统入口点，包含示例智能体的创建和使用
- `Agent/Agent_base.py` - BaseAgent类，提供核心功能
- `Agent/Agent_list.py` - 智能体注册和管理
- `Agent/tools.py` - 工具函数实现
- `Agent/agent.py` - 智能体相关功能

### 文件树
- Agent
  - __init__.py
  - Agent_Base_.py
  - Agent_list.py
  - 
## 安装与配置

### 环境要求

- Python >= 3.12
- 依赖包见 `pyproject.toml`

### 安装步骤

1. 克隆项目：
   ```bash
   git clone https://github.com/Secret-Dumplings/AI_Company.git
   cd AI_Company
   ```

2. 安装依赖：
使用uv（自行安装）：
   ```bash
   uv sync
   ```

### 环境变量配置

在项目根目录创建 `.env` 文件并配置以下变量：

```env
API_KEY=your_api_key_here
```

## 使用方法

### 创建智能体

在 `main.py` 中定义新的智能体类：

```python
@Agent.register_agent(uuid.uuid4().hex, "agent_name")
class MyAgent(Agent.BaseAgent):
    prompt = "智能体的角色提示词"
    api_provider = "API端点"
    model_name = "模型名称"
    api_key = os.getenv("API_KEY")

    def __init__(self):
        super().__init__()
```

### 运行系统

```bash
uv run main.py
```

## 智能体通信

智能体可以通过 `<ask_for_help>` XML标签与其他智能体通信：

```xml
<ask_for_help>
    <agent_id>目标智能体ID</agent_id>
    <message>消息内容</message>
    <your_id>发送方ID</your_id>
</ask_for_help>
```

## 项目特点

1. **模块化设计** - 易于扩展和维护
2. **多智能体协作** - 支持复杂的任务分解和协作
3. **工具调用** - 通过XML标签灵活调用各种工具
4. **流式响应** - 支持流式数据处理，实时显示结果
5. **用量统计** - 自动统计API调用的token用量

## 贡献

欢迎提交Issue和Pull Request来改进项目。

## 许可证

[Apache-2.0 license](https://github.com/Secret-Dumplings/AI_Company#Apache-2.0-1-ov-file)