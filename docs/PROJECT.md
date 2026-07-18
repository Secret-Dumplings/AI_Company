# AI Company 项目文档

> 基于 LLM 的多智能体协作框架 — 让一群 AI 像公司员工一样协同完成任务。

---

## 目录

- [一、项目概况](#一项目概况)
- [二、详细介绍](#二详细介绍)
- [三、如何使用](#三如何使用)
- [四、希望遵守的开发规范](#四希望遵守的开发规范)

---

## 一、项目概况

### 1. 是什么

**AI Company** 是一个面向多智能体协作的 Python 框架，核心目标是把"一群 LLM 智能体"组织成可协作的"AI 公司"。

它由两部分组成：

| 部分 | 路径 | 角色 |
|------|------|------|
| **Dumplings（核心库）** | `Dumplings/` | 可独立安装、可被其他项目以 `uv add` 方式引用的框架包 |
| **AI_Company（演示应用）** | 项目根目录 | 以 Dumplings 为依赖、组装实际业务 Agent 的示例项目 |

> Dumplings 是 AI Company 的引擎；AI_Company 是基于该引擎构建的"示例公司"。两者通过 `uv` 的 workspace 机制绑定（见 `pyproject.toml` 的 `[tool.uv.workspace]`）。

### 2. 核心能力一览

- **多 Agent 注册管理**：`@register_agent(uuid, name)` 双键（UUID + 名称）注册到全局 `agent_list`
- **双模式工具调用**：优先使用 **Function Calling**（`fc_model=True`），XML 作为下位兼容
- **细粒度权限控制**：工具可通过 `allowed_agents` 白名单指定哪些 Agent 能调用
- **XML 标签通信协议**：`<ask_for_help>` `<list_agents>` `<attempt_completion>` 等
- **MCP（Model Context Protocol）集成**：通过 `mcp_bridge` 把外部 MCP 服务器工具自动注册到 `tool_registry`
- **Skill 开放标准**：兼容 `.claude/skills/` 目录，让 Agent 自动发现并调用 Skills
- **流式响应 + 结构化日志**：基于 `requests` 流式拉取 + `loguru` 日志
- **多模态输入**：`conversation_with_tool(messages, images=...)` 支持 base64 / URL 图片
- **钩子系统**：`register_tool_hook()` 监听工具调用前/后/错误事件

### 3. 技术栈

- **语言**：Python ≥ 3.10
- **包管理**：`uv`（清华源）
- **依赖核心**：`requests`、`beautifulsoup4`、`loguru`、`lxml`、`mcp`、`openai`
- **协议**：OpenAI-compatible Chat Completions（REST）
- **可选 Web 集成（已声明但当前未在示例中使用）**：`fastapi`、`flask`、`streamlit`、`python-socketio`、`uvicorn`

### 4. 适用场景

- 多角色协作类任务（调度 + 工具专精 Agent）
- 子 Agent 委派 / Agent 编排实验
- MCP 工具桥接与 Skills 系统实验
- 学习"装饰器注册 + 全局字典"模式的轻量框架实现

---

## 二、详细介绍

### 1. 项目结构

```
AI_Company/
├── Dumplings/                       # 核心框架包（独立可发布的 wheel）
│   ├── __init__.py                  # 模块导出 + help() 速查
│   ├── Agent_Base_.py              # BaseAgent 抽象类：对话/工具/历史/钩子
│   ├── Agent_list.py                # register_agent + agent_list 全局注册表
│   ├── agent_tool.py                # tool 类 + tool_registry 单例
│   ├── mcp_bridge.py                # MCP 服务器工具自动注册与会话池
│   ├── skill.py                     # Skill 注册表（与 .claude/skills 协议对接）
│   ├── skill_bridge.py              # Skill 与 tool_registry 之间的桥接
│   ├── logging_config.py            # 统一 loguru 配置（按 LOGURU_LEVEL 切换）
│   ├── LOGGING_GUIDELINES.md        # 日志级别使用规范
│   ├── README.md                    # 框架独立文档
│   ├── LICENSE                      # Apache 2.0
│   └── pyproject.toml               # Dumplings 包的元数据
│
├── examples/                        # AI Company 侧的运行示例
│   ├── basic_agent/agent_example.py          # 单 Agent + 工具示例
│   └── multi_agent/ask_for_help_example.py   # 多 Agent + ask_for_help 示例
│
├── docs/                            # 文档目录（当前仅存 index.md）
│   └── index.md
│
├── main.py                          # AI Company 主入口（演示 scheduling_agent）
├── docs.md                          # 长文档：如何开发 Agent
├── README.md                        # 中英双语 README（同时面向仓库用户和 Agent 协作）
├── pyproject.toml                   # 项目元数据 + uv workspace 声明
├── uv.lock                          # 锁定依赖版本
├── .env / .env.example              # API_KEY 配置
├── .gitmodules / .venv / .pytest_cache / .idea / __pycache__ ...
└── logs/app.log                     # 日志输出（运行时生成）
```

### 2. 核心组件详解

#### 2.1 `register_agent` + `agent_list`（`Dumplings/Agent_list.py`）

```python
agent_list = {}          # 双键字典: {uuid: instance, name: instance}

def register_agent(uuid, name, description=None):
    def _decorator(cls):
        cls.uuid = uuid
        cls.name = name
        cls.description = description
        instance = cls()                  # 立刻实例化一次
        agent_list[uuid] = instance
        agent_list[name] = instance
        return cls
    return _decorator
```

要点：
- 一个类同时挂在两个键下（UUID + name），内存中只有一份实例
- 注册时**立即实例化**（`cls()`），所以 Agent 必须有无参 `__init__`
- 注册完成后，通过 `Dumplings.agent_list["name"]` 或 `[uuid]` 都能取到同一个实例

#### 2.2 `BaseAgent`（`Dumplings/Agent_Base_.py`）

继承 `Dumplings.BaseAgent`（实际导出名为 `Agent`），必须设置 4 个类属性：

| 属性 | 必填 | 用途 |
|------|------|------|
| `prompt` | ✅ | 系统提示词 |
| `api_provider` | ✅ | OpenAI-compatible Chat Completions URL |
| `model_name` | ✅ | 模型名 |
| `api_key` | ✅ | Bearer Token |
| `fc_model` | 否（默认 `True`）| 是否用 Function Calling |
| `stream` | 否（默认 `True`）| 流式响应 |
| `description` | 否 | Agent 简介，便于其他 AI 调用方引用 |

初始化时做的事：
1. 把 `cls.uuid` / `cls.name` 复制到实例
2. 调用 `tool_registry.register_agent_uuid(uuid, name)` 建立 uuid→name 映射
3. 拉取该 Agent 有权限的工具列表，**动态拼装** `tools_prompt` 并塞到 `prompt` 末尾
4. 自动追加内建工具（`ask_for_help` / `list_agents` / `attempt_completion` / `reload`）提示
5. 通过 `skill_registry.get_skills_prompt_text()` 注入 Skills 信息
6. 异步线程跑一次连通性测试（`Connectivity`），不阻塞主流程

关键方法：

| 方法 | 作用 |
|------|------|
| `conversation_with_tool(messages, tool=False, images=None)` | 主对话入口，支持文本 + 图片 + 工具调用 |
| `register_tool_hook(hook_func)` | 注册工具调用钩子（`before` / `after` / `error`） |
| `_execute_hooks(...)` | 内部触发所有已注册钩子 |
| `ask_for_help(agent_id, message)` | 请求其他 Agent 帮助 |
| `list_agents()` | 列出全部 Agent |
| `attempt_completion(report_content)` | 标记任务完成 |
| `reload()` | 重新拼装系统提示词以反映工具/Skills 变化 |
| `out(content)` | 输出回调，可被重写以劫持输出流 |

#### 2.3 `tool_registry`（`Dumplings/agent_tool.py`）

全局工具注册器（单例 `tool_registry = tool()`）。

注册签名（**请按此顺序传参，避免命名混淆**）：

```python
@Dumplings.tool_registry.register_tool(
    allowed_agents=None,            # str | List[str] | None（None=全体可用）
    description="...",              # 工具描述
    name="tool_name",               # 工具名（默认 = 函数名）
    parameters={...}                # OpenAI function calling JSON Schema
)
```

内部维护：
- `_tools: dict[name → info]`：含 `function`、`allowed_agents`、`description`、`schema` 等
- `_uuid_to_name: dict`：在 Agent 初始化时建立，方便权限检查时按 uuid 查找 name

权限检查语义（见 `check_permission`）：
1. 工具名不存在 → 拒绝并 `WARNING`
2. `allowed_agents is None` → 全员放行
3. agent 名（转换自 uuid 后）不在白名单 → 拒绝

#### 2.4 内建工具（自动注册到每个 Agent）

`Agent.__init__` 会把下面这些"如果 Agent 类上有同名方法，就当作可用工具"自动注册：

| 工具名 | 用途 | 主要参数 |
|--------|------|----------|
| `ask_for_help` | 请求另一个 Agent 协助 | `agent_id`(UUID或name), `message` |
| `list_agents` | 列出全部已注册 Agent | 无 |
| `attempt_completion` | 标记任务完成并停止对话 | `report_content`(可选) |
| `reload` | 重新拉取工具列表/Skills，重置 system prompt | 无 |

> 这些工具同时支持 Function Calling 和 XML 两种调用方式。

#### 2.5 MCP 桥接（`Dumplings/mcp_bridge.py`）

```python
from Dumplings.mcp_bridge import register_mcp_tools, start_health_check
Dumplings.register_mcp_tools("path/to/mcp_server.py")
start_health_check(interval=300)
```

行为：
- 启动 MCP 子进程，把服务器暴露的 tools 自动包装进 `tool_registry`
- 维护全局会话池 `_global_session_pool`，对 session 做健康检查与自动回收
- 提供 `close_all_mcp_sessions_sync()`、`mcp_session_context()` 等同步/异步上下文

#### 2.6 Skill 系统（`Dumplings/skill.py` + `skill_bridge.py`）

- `skill_registry` 扫描 `.claude/skills/` 或任意目录，把符合 Skill 规范的子目录注册进来
- 通过 `skill_bridge` 把 Skill "伪装"成普通工具挂到 `tool_registry`，所以 Agent 完全无感知
- Agent 在初始化时，Skill 会以 Prompt 文本 + Function Calling Schema 两种形式同时注入

#### 2.7 日志（`Dumplings/logging_config.py` + `LOGGING_GUIDELINES.md`）

- 控制台 + `logs/app.log` 双路输出
- 级别由环境变量 `LOGURU_LEVEL` 控制：默认不显式设置时按代码内默认值
- **强制规范**：禁止把完整 prompt / history / 工具参数原文用 INFO/DEBUG 级别记录（详见第四节）

### 3. 调用链路总览

```
用户 ──▶ agent.conversation_with_tool("...")
            │
            ├──▶ 拼 payload（含 tools schema + history）
            ├──▶ requests.post(api_provider, stream=True)
            │
            ├──▶ 流式解析 SSE chunk
            │     ├─ 文本片段 ──▶ self.out({"message": ...}) ──▶ 控制台/日志
            │     └─ tool_calls ──▶ 注册工具钩子(before) ──▶ 执行 ──▶ 钩子(after) ──▶ 把结果回灌 history
            │
            └──▶ 检测到 <attempt_completion> ──▶ self.out({"task": ...}) ──▶ 结束对话
```

`ask_for_help` 的调用过程本质就是：当前 Agent 通过 `function_call` 调用内置工具 `ask_for_help`，框架根据 `agent_id` 取到目标 Agent 实例，直接调用 `target.conversation_with_tool(message)`，把对方的返回拼回 history，从而实现"对话嵌套"。

---

## 三、如何使用

### 1. 环境准备

- Python ≥ 3.10
- 安装 [`uv`](https://github.com/astral-sh/uv)
- 一个能调用 OpenAI-compatible Chat Completions 的 API Key

### 2. 克隆与安装

```bash
git clone https://github.com/Secret-Dumplings/AI_Company.git
cd AI_Company
uv sync
```

`pyproject.toml` 用 uv workspace 把 `Dumplings/` 作为本地包自动链接，无需手动 `pip install`。

### 3. 配置 API Key

复制 `.env.example` 为 `.env` 并填写：

```env
API_KEY="sk-XXX"
```

代码中通过 `os.getenv("API_KEY")` 取用（见 `main.py`）。

### 4. 运行自带示例

```bash
# 顶层演示：调度 Agent 请求时间 Agent
uv run main.py

# 基础 Agent 示例
uv run examples/basic_agent/agent_example.py

# 多 Agent 协作示例
uv run examples/multi_agent/ask_for_help_example.py
```

### 5. 编写你自己的 Agent

最小可运行模板：

```python
import os, uuid
from dotenv import load_dotenv
import Dumplings

load_dotenv()

# 1. 可选：注册一个工具（Function Calling 模式）
@Dumplings.tool_registry.register_tool(
    allowed_agents=["my_agent"],   # None/[] 表示全员可用
    description="查询某城市天气",
    name="get_weather",
    parameters={
        "type": "object",
        "properties": {
            "city": {"type": "string", "description": "城市名"}
        },
        "required": ["city"]
    },
)
def get_weather(city: str) -> str:
    return f"{city}今天晴，温度 25°C"

# 2. 注册 Agent
@Dumplings.register_agent(uuid.uuid4().hex, "my_agent", "你的Agent简介")
class MyAgent(Dumplings.BaseAgent):
    prompt = "你是一个天气助手，使用 get_weather 查询天气。"
    api_provider = "https://api.example.com/v1/chat/completions"
    model_name   = "model_name"
    api_key      = os.getenv("API_KEY")
    fc_model     = True            # 默认开启

    def __init__(self):
        super().__init__()

if __name__ == "__main__":
    agent = Dumplings.agent_list["my_agent"]
    agent.conversation_with_tool("帮我查一下北京的天气")
```

Agent 也可以定义 `description`：

```python
@Dumplings.register_agent(uuid.uuid4().hex, "weather_agent", "天气查询专家，支持多城市")
```

**注意**：`description` 在 `BaseAgent` 中已存在类属性，但当前 `Agent.__init__` 主要使用 `cls.prompt` / `cls.uuid` / `cls.name`，description 仅作元信息暴露。如需在 prompt 中引用，可以重写 `__init__`：

```python
class MyAgent(Dumplings.BaseAgent):
    def __init__(self):
        self.prompt = self.prompt + f"\n（描述：{self.__class__.description}）"
        super().__init__()
```

### 6. 多 Agent 协作

```python
# 注册多个 Agent 后，让主 Agent 通过 ask_for_help 调用子 Agent
@Dumplings.register_agent(uuid.uuid4().hex, "scheduler")
class Scheduler(Dumplings.BaseAgent):
    prompt = (
        "你是调度 Agent。当用户需要查时间时，使用 ask_for_help 调用 "
        "time_agent；当用户需要查天气时，调用 weather_agent。"
    )
    api_provider = "https://api.example.com/v1/chat/completions"
    model_name   = "model_name"
    api_key      = os.getenv("API_KEY")
    fc_model     = True

    def __init__(self):
        super().__init__()

Dumplings.agent_list["scheduler"].conversation_with_tool(
    "现在几点了？顺便查下北京天气。"
)
```

### 7. 启用 MCP 工具

```python
from pathlib import Path
from Dumplings.mcp_bridge import register_mcp_tools

# 让 MCP 服务器的所有工具注册到 tool_registry
register_mcp_tools(
    server_path=Path("mcp/weather_mcp/weather_server.py"),
    register_resources=True,
    allowed_agents=["weather_agent"],
)
```

### 8. 接入 Skills

```bash
# 标准 Skill 目录结构
.claude/skills/my-skill/
├── SKILL.md
└── scripts/
```

```python
Dumplings.skill_registry.scan_and_register([Path(".")])
# Skills 会自动出现在 Agent 的工具列表 / 系统提示词中
```

### 9. 自定义 Agent 行为

```python
class MyAgent(Dumplings.BaseAgent):
    # 自定义流式输出
    def out(self, content):
        if content.get("tool_name"):
            print(f"\n→ tool {content['tool_name']} {content.get('tool_parameter')}")
            return
        if content.get("task"):
            print("\n[done]")
            return
        print(content.get("message", ""), end="")

    # 注册工具调用钩子
    def __init__(self):
        super().__init__()
        self.register_tool_hook(self._audit_hook)

    def _audit_hook(self, event_type, tool_name, tool_args, tool_result=None, task_id=None):
        logger.info(f"[{event_type}] {tool_name} args={tool_args}")
```

### 10. 实用查询速查

```python
# 列出所有已注册工具
print(Dumplings.tool_registry.list_tools())

# 列出某个 Agent 可用的工具
print(Dumplings.tool_registry.get_all_tools_info("uuid-or-name"))

# 查看 Agent 历史
print(Dumplings.agent_list["my_agent"].history)

# 关闭 MCP 会话
from Dumplings.mcp_bridge import close_all_mcp_sessions_sync
close_all_mcp_sessions_sync()
```

### 11. 常用环境变量

| 变量 | 作用 | 取值示例 |
|------|------|----------|
| `API_KEY` | LLM 鉴权 token（Bearer） | `sk-...` |
| `LOGURU_LEVEL` | 全局日志级别 | `TRACE` / `DEBUG` / `INFO` / `WARNING` |
| `LOGURU_DISABLED` | 关闭 loguru 初始化 | `1` |

---

## 四、希望遵守的开发规范

> 这一节既是约束也是建议；任何同时被本项目接受的 PR 都应满足这些条款。

### 1. 工具实现原则

- **接口签名宽容**：使用 `**kwargs` 或显式形参均可，但形参名需与 `parameters.properties` 中的 key 一一对应
- **幂等且无状态**：同参数多次调用应返回相同结果，不依赖外部隐藏状态
- **错误不要抛异常**：捕获异常并返回字符串错误信息（"执行失败：xxx"），避免打断对话循环
- **避免在工具中调用 LLM**：工具应当是确定性函数；如必须调用 LLM，请走 Agent 委派（`ask_for_help`）
- **描述简短准确**：description 是 LLM 决定是否调用你的依据，建议 ≤ 1 句话，含关键参数语义
- **`parameters` 必须填完整 JSON Schema**：包括 `type` / `properties` / `required`，不要为了图省事留空

### 2. 工具权限原则

- **显式白名单优于隐式放开**：能用 `allowed_agents=["xxx"]` 明确指定就不要留 `None`
- **跨 Agent 复用工具要谨慎**：跨 Agent 共享的工具可能放大副作用，请评估后启用
- **保持 uuid 映射一致**：`register_agent` 与 `tool_registry.register_agent_uuid` 由框架自动联动，**不要手动重复注册**

### 4. Function Calling vs XML

- **首选 Function Calling**（`fc_model=True`）：参数解析准确、结构清晰，是项目主路径
- **XML 仅为下位兼容**：内部 `Agent_Base_.py` 顶部已明确标注"xml 工具调用改为下位支持"，新工具仅在 Function Calling 模式下编写
- 在 prompt 中如混用两种协议，请在工具描述里写明调用格式

### 5. 日志规范（强约束）

遵循 `Dumplings/LOGGING_GUIDELINES.md`：

| 级别 | 允许内容 | 禁止内容 |
|------|----------|----------|
| `TRACE` | 流式 chunk、原始响应 JSON、装饰器内部流程 | — |
| `DEBUG` | 工具调用参数（脱敏）、流程状态、对象长度 | 完整 JSON 响应体 |
| `INFO` | Agent 连接状态、服务启动/停止、注册成功数 | 完整 prompt、完整 history、完整工具参数 |
| `WARNING` | 工具未找到、未授权访问 | — |
| `ERROR` | 单个工具执行失败、API 错误、关闭会话失败 | — |
| `CRITICAL` | 核心服务崩溃 | — |

- **不要把 API Key、对话内容、用户隐私信息写入日志**
- 推荐通过 `from Dumplings.logging_config import setup_logging` 统一初始化
- 提交 PR 前用 `LOGURU_LEVEL=INFO` 自查一次：不应该看到 prompt 内容或长 history

### 6. 异常与健壮性

- 钩子实现必须自行 `try/except`，钩子崩溃不应阻断对话（参考 `_execute_hooks` 实现）
- 工具函数必须自行 `try/except`，返回字符串错误而非抛错
- Agent 初始化是**同步**完成的，注册期间的失败会立即抛错，请在脚本入口处显式捕获

### 7. 依赖与代码组织

- **不要新增重型框架**：Dumplings 鼓励"轻 + 协议"，如需新增中间件，请在 `Dumplings/` 内加包并在 `__init__.py` 集中导出
- **新增示例请放到 `examples/<主题>/xxx.py`**，并在 `main.py` 或 `README.md` 中给出运行命令
- **保持工作区结构**：`Dumplings` 作为子包加入 `[tool.uv.workspace]`；任何子包修改都对根项目立即可见
- **API 兼容性**：目前面向 OpenAI-compatible Chat Completions 设计，**不要**将 Anthropic/Gemini 等专有协议写进核心，可在 `BaseAgent` 派生

### 8. 提交与变更约定

- 中文/英文提交信息都可，但建议中英对照，遵守"修复 bug / 增加功能 / 优化结构"三类关键词
- 修改 `Dumplings/` 后建议在 README 或 docs 中同步更新对应章节
- 引入新的环境变量时，请在本文件"常用环境变量"小节追加

### 9. 安全与合规

- **不要把 `.env`、`uv.lock` 之外的任何密钥写入仓库**
- 通过 `tool_registry` 暴露的工具默认仅项目内部 Agent 可见；如需对外暴露，请在工具函数中再校验调用方（见 `_uuid_to_name` 机制）
- MCP 服务器默认通过 stdio 拉起，请仅注册可信来源

---

## 附录 A：常见问题速查

**Q1：Agent 注册后调用报"找不到工具"？**
1. 确认工具的 `allowed_agents` 列表包含该 Agent 的 UUID 或 name
2. 确认 prompt 中确实告诉 LLM 可以使用该工具（系统将自动补充prompt请检查注册情况）
3. 调 `Dumplings.tool_registry.get_all_tools_info(uuid)` 验证

**Q2：Agent 之间 `ask_for_help` 后没反应？**
1. 确认目标 Agent 已注册（`name` 或 `uuid` 不打错）
2. 确认目标 Agent 的 `fc_model=True` 或正确写了 XML 标签
3. 看 `logs/app.log` 中是否有 WARNING/ERROR

**Q3：怎么让 Agent 看见我新加的工具？**
调用 `Dumplings.agent_list["my_agent"].reload()`，或在脚本入口重新 `import` 并让 Agent 重新初始化。

**Q4：怎么调试提示词？**
- 临时把 `LOGURU_LEVEL=DEBUG` 看流程
- `print(agent.history)` 看实际注入的 system prompt
- 重写 `out()` 方法拦截原始 chunk

---

## 附录 B：与官方 SDK 的功能差距

> 本节对比 `Dumplings.BaseAgent` / `Dumplings.AnthropicAgent` 与
> [`openai-python`](https://github.com/openai/openai-python) /
> [`anthropic-sdk-python`](https://github.com/anthropics/anthropic-sdk-python)
> 官方 Python SDK，解释我们在哪里做了简化、哪些能力尚未实现。

### 官方 SDK 提供但本框架未提供（或部分实现）

| 能力 | openai-python | anthropic-sdk-python | 本框架 |
|------|---------------|----------------------|--------|
| 自动重试（含指数退避 + jitter） | ✅ 默认 2 次，仅对幂等请求生效 | ✅ | ❌ 调用层无重试，依赖用户包 try/except |
| 统一 timeout / 连接 / 读取超时 | ✅ `timeout=` 入参 | ✅ | ⚠️ 写死在 `_call_blocking` / `_call_stream` 内部，未暴露 |
| 错误类型体系（`APIError` / `RateLimitError` 等） | ✅ | ✅ | ❌ 只在 `logger.error` 后 `raise RuntimeError` |
| Async client | ✅ `AsyncOpenAI` | ✅ `AsyncAnthropic` | ❌ 全部基于 `requests` 同步，阻塞；多 Agent 并发需自起线程 |
| 流处理上下文管理器 + 事件钩子 | ✅ `client.messages.stream()` | ✅ | ⚠️ 自行实现 SSE 解析，没有官方那种高阶事件类型 |
| Prompt cache 头（`prompt-caching-...`） | ✅ | ✅（Anthropic 2024+） | ❌ |
| Extended thinking / reasoning effort（o1 / Claude reasoning） | ✅ | ✅ | ❌ |
| 内置工具（web_search / file_search / code_execution） | ✅ | ⚠️ 部分 beta | ❌ |
| 结构化输出（`response_format` / JSON schema 校验） | ✅ | ✅（tool input_schema 校验） | ❌ |
| Token 计数 / tiktoken | ✅ | ❌ | ⚠️ 只在流式 `stream_options.include_usage` 拿到原始值 |
| 文件上传 / batches | ✅ | ⚠️ 部分 | ❌ |
| 自定义 HTTP client / httpx 注入 / proxies | ✅ | ✅ | ❌ |
| Pydantic 化请求/响应模型 | ✅ | ✅ | ❌ 全部 dict/dict |
| 多 region / 数据中心 / 拦截器 / global hooks | ✅ | ✅ | ⚠️ 仅有 per-Agent 工具钩子 |

### 本框架提供但官方 SDK 不提供

| 能力 | 说明 |
|------|------|
| **多 Agent 编排** | `agent_list` 双键（UUID + 名称）注册与查找；`ask_for_help` 跨 Agent 调用 |
| **自动任务完成检测** | `attempt_completion` 内置工具 + 自动停机语义 |
| **统一 tool permission ACL** | `allowed_agents` 精细到每个工具 |
| **统一 agent 发现** | `list_agents` 内置工具，对 LLM 暴露 |
| **XML 模式工具调用**（降级路径） | 对不支持 Function Calling 的模型仍能跑通 |
| **钩子系统** | `register_tool_hook(event_type, tool_name, args, result, task_id)` |
| **运行时声明式重载** | `reload()` 重置 system prompt / 工具 / Skills 上下文 |
| **Skill 开放标准** | 兼容 `.claude/skills/` 目录，扫描/监控/自动注册 |
| **MCP 协议桥接** | 拉起 stdio MCP 服务器并自动注册其工具 |

### 实现路线建议（按代价排序）

1. **超时与重试**（小） — 在 `_call_blocking` / `_call_stream` 引入装饰器，按 status code 决定重试
2. **Async client**（中） — 把 `requests` 换成 `httpx.AsyncClient`，把 `conversation_with_tool` 改成 `async def`
3. **错误类型**（小） — `class AnthropicError` 继承 `Exception`，按 status code 细分 `RateLimitError` / `BadRequestError`
4. **结构化输出**（中） — 在 `register_tool` 上加 `response_schema=pydantic.Model`，框架自动校验 LLM 返回
5. **tiktoken token 计数**（小） — 离线估算 prompt token，省去调用方自己计费的负担
6. **Pydantic 模型**（中） — 用 `pydantic.BaseModel` 替换 dict 在 Agent / Tool API 处

---

## 附录 C：`AnthropicAgent` 使用指南

> 新增于 2026 年，对应 `Dumplings/Anthropic` 协议。整个体验与 `BaseAgent` 一致，仅协议层不同。

### 安装与配置

```bash
# Anthropic 协议不强制 SDK 依赖（我们走 raw HTTP），仅需 requests
uv sync
export ANTHROPIC_API_KEY=sk-ant-xxx
export ANTHROPIC_BASE_URL=https://api.anthropic.com   # 可选
export ANTHROPIC_MODEL=claude-3-5-sonnet-latest       # 可选
```

### 最小可用示例

```python
import os, uuid
from dotenv import load_dotenv
import Dumplings

load_dotenv()

@Dumplings.tool_registry.register_tool(
    allowed_agents=["weather_agent"],
    description="查询某城市的天气",
    name="get_weather",
    parameters={
        "type": "object",
        "properties": {"city": {"type": "string", "description": "城市名"}},
        "required": ["city"],
    },
)
def get_weather(city: str) -> str:
    return f"{city}今天晴，25°C"

@Dumplings.register_agent(uuid.uuid4().hex, "weather_agent", "天气小助手")
class WeatherAgent(Dumplings.anthropic_agent.AnthropicAgent):
    prompt = "你是天气助手，调用 get_weather 拿天气；用 attempt_completion 汇报。"
    api_provider = "https://api.anthropic.com"
    model_name   = "claude-3-5-sonnet-latest"
    api_key      = os.getenv("ANTHROPIC_API_KEY")

agent = Dumplings.agent_list["weather_agent"]
agent.conversation_with_tool("请帮我查一下北京今天的天气")
```

可运行版本：[`examples/anthropic_agent/agent_example.py`](../examples/anthropic_agent/agent_example.py)

### 与 `BaseAgent` 的差异

| 维度 | `BaseAgent` | `AnthropicAgent` |
|------|-------------|------------------|
| 协议 | OpenAI-compatible Chat Completions | Anthropic Messages API |
| 鉴权头 | `Authorization: Bearer ...` | `x-api-key: ...` + `anthropic-version: ...` |
| `system prompt` | 一条 `role=system` 的消息 | 顶层 `system` 字段 |
| 工具 schema | `{type:"function", function:{...}}` | 顶层 `{name, description, input_schema}` |
| 工具调用消息 | assistant 携带 `tool_calls` + tool role 消息 | assistant 携带 `tool_use` 块；用户消息携带 `tool_result` 块 |
| 流式事件 | `chunk.choices[0].delta` | `message_start` / `content_block_start` / `content_block_delta` / `content_block_stop` / `message_delta` / `message_stop` |
| 多模态 | `{"type": "image_url", ...}` | `{"type": "image", "source": {...}}` |
| 内置工具调用方式 | XML + Function Calling | 仅 Function Calling（`tool_use`） |
| 公共能力 | `ask_for_help` / `list_agents` / `attempt_completion` / `reload` / `register_tool_hook` / `out` | （完全一致） |

### 通用装饰器：`@builtin_tool`

不论用哪个协议，Agent 的内置工具都通过 `Dumplings.agent_tool.builtin_tool` 声明，**不再有硬编码 schema**：

```python
from Dumplings import builtin_tool

class MyAgent(Dumplings.anthropic_agent.AnthropicAgent):
    @builtin_tool(
        description="发一条 Slack 通知",
        params={"channel": "频道名", "text": "消息内容"},
    )
    def send_slack(self, channel: str, text: str) -> str:
        """实际发送逻辑"""
        return f"sent to {channel}"

    @builtin_tool(
        description="求两数之和",
    )
    def add(self, a: float, b: float) -> float:
        return a + b
```

**自动推导**：
- `input_schema.properties` ← 函数签名（参数名 + 类型注解）
- `input_schema.required`   ← 没有默认值的参数
- `description`             ← 装饰器显式传入 / 函数 docstring 第一段
- 参数的 `description`     ← 装饰器 `params` 字典 / docstring `Args:` / Sphinx `:param:` / 参数名兜底

**子类继承自动传播**：子类覆盖 `@builtin_tool` 装饰的方法即使没有重新装饰，框架也通过 `_builtin_promote_overrides` 自动复用父类的 meta，无需重复声明。

### 公共的多 Agent 协作

两个协议共享同一份 `agent_list` / `tool_registry` / `skill_registry`：

```python
@Dumplings.register_agent(uuid.uuid4().hex, "scheduler")
class Scheduler(Dumplings.BaseAgent):           # OpenAI 协议
    prompt = "..."
    api_provider = "https://coding.dashscope.aliyuncs.com/v1/chat/completions"
    model_name   = "qwen3.5-plus"
    api_key      = os.getenv("API_KEY")
    fc_model     = True

@Dumplings.register_agent(uuid.uuid4().hex, "weather")
class Weather(Dumplings.anthropic_agent.AnthropicAgent):  # Anthropic 协议
    ...

# scheduler 可直接 ask_for_help 把任务分发给 weather，反之亦然
Dumplings.agent_list["scheduler"].conversation_with_tool(
    "请 request_weather 帮你查一下北京的天气"
)
```

### 局限与待办

- ❌ 当前无 retry / timeout 配置
- ❌ 当前仅 sync；如需并发请另起线程
- ❌ 不支持 extended thinking / prompt cache 头
- ❌ 不读取 Anthropic `usage` 字段做费用统计
- ❌ 不支持 batch / 文件上传类业务

---

## 附录 D：文件交叉索引

| 主题 | 文件 |
|------|------|
| Agent 基类（OpenAI 协议） | `Dumplings/Agent_Base_.py` |
| Agent 基类（Anthropic 协议） | `Dumplings/anthropic_agent.py` |
| Agent 注册 | `Dumplings/Agent_list.py` |
| 工具注册 + `@builtin_tool` 装饰器 | `Dumplings/agent_tool.py` |
| MCP 桥接 | `Dumplings/mcp_bridge.py` |
| Skill 系统 | `Dumplings/skill.py`、`Dumplings/skill_bridge.py` |
| 日志 | `Dumplings/logging_config.py`、`Dumplings/LOGGING_GUIDELINES.md` |
| 顶层示例 | `main.py`、`examples/basic_agent/agent_example.py`、`examples/multi_agent/ask_for_help_example.py` |
| Anthropic 协议示例 | `examples/anthropic_agent/agent_example.py` |
| 完整开发指南 | `docs.md` |
| 项目说明 | `README.md` |
| 框架独立文档 | `Dumplings/README.md` |

---

<p align="center">
— 文档随仓库演化；不一致处请以源码为准 —<br/>
AI Company · 2026
</p>