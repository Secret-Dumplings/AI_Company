# AI Company API 扩展层

把 [`dumplingsAI`](../Dumplings/) 暴露为 HTTP API，让远程客户端（Web 前端 / 移动端 / CLI / 其他服务）
通过 HTTP 调用 Agent。**`dumplingsAI` 子包完全不动**——本目录是 *纯扩展*。

## 架构

```
┌─────────────────────────────────────────────────┐
│  HTTP Client（curl / openai-python / fetch）    │
└────────────────────┬────────────────────────────┘
                     │  HTTP + JSON / SSE
                     ▼
┌─────────────────────────────────────────────────┐
│  AI Company API  (FastAPI)        ← 本目录     │
│  /health /agents /skills /mcp /tools ...        │
└────────────────────┬────────────────────────────┘
                     │  Python API
                     ▼
┌─────────────────────────────────────────────────┐
│  dumplingsAI  (BaseAgent / AnthropicAgent /     │
│  tool_registry / agent_list / llm_transport)    │
└─────────────────────────────────────────────────┘
```

## 快速开始

### 1. 写 Agent 配置

编辑 [`examples/api/agents_config.py`](../examples/api/agents_config.py)：

```python
import os, uuid
import dumplingsAI

@dumplingsAI.register_agent(uuid.uuid4().hex, "my_agent")
class MyAgent(dumplingsAI.BaseAgent):
    prompt = "你是一个助手"
    api_provider = "https://api.example.com/v1/chat/completions"
    model_name = os.getenv("OPENAI_MODEL")
    api_key = os.getenv("OPENAI_API_KEY")
```

### 2. 启动服务

```bash
# 默认加载 examples/api/agents_config.py
uv run uvicorn api.app:app --reload --port 8000

# 或指定自己的配置
AGENTS_CONFIG=/path/to/my_agents.py uv run uvicorn api.app:app --reload

# 不加载任何 agent（用于测试 API 本身）
AGENTS_CONFIG="" uv run uvicorn api.app:app --reload
```

### 3. 调用 API

#### 健康检查

```bash
curl http://localhost:8000/health
# {"status":"ok","version":"0.2.2","n_agents":2,"n_tools":1}
```

#### 列出所有 Agent

```bash
curl http://localhost:8000/agents | python -m json.tool
```

#### 与 Agent 对话（OpenAI 兼容风格，非流式）

```bash
curl -X POST http://localhost:8000/agents/my_agent/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [
      {"role": "user", "content": "你好"}
    ]
  }'
```

返回：

```json
{
  "id": "chatcmpl-...",
  "object": "chat.completion",
  "choices": [
    {
      "index": 0,
      "message": {"role": "assistant", "content": "你好！有什么可以帮你的吗？"},
      "finish_reason": "stop"
    }
  ],
  "agent_name": "my_agent",
  "agent_uuid": "..."
}
```

#### 与 Agent 对话（流式 SSE）

```bash
curl -N -X POST http://localhost:8000/agents/my_agent/chat \
  -H "Content-Type: application/json" \
  -d '{
    "messages": [{"role": "user", "content": "你好"}],
    "stream": true
  }'
```

返回 `text/event-stream`，每帧一个 JSON：

```
data: {"event": "text", "data": {"delta": "你"}, "agent_name": "my_agent"}

data: {"event": "text", "data": {"delta": "好"}, "agent_name": "my_agent"}

data: {"event": "done", "data": {"finish_reason": "stop"}, "agent_name": "my_agent"}
```

事件类型：`text` / `tool_call` / `tool_result` / `done` / `error`。

#### 用 openai-python 客户端（零改动）

请求 / 响应形状对齐 OpenAI Chat Completions：

```python
import openai

client = openai.OpenAI(
    base_url="http://localhost:8000",
    api_key="not-used",        # API key 在 server 端配置
)

rsp = client.chat.completions.create(
    model="my_agent",
    messages=[{"role": "user", "content": "你好"}],
)
print(rsp.choices[0].message.content)
```

#### 列出 Agent 可用的工具

```bash
curl http://localhost:8000/agents/my_agent/tools | python -m json.tool
```

#### 运行时注册 Agent

```bash
curl -X POST http://localhost:8000/agents \
  -H "Content-Type: application/json" \
  -d '{
    "name": "rt_agent",
    "protocol": "openai",
    "prompt": "你是一个助手",
    "model_name": "gpt-4",
    "api_key": "sk-..."
  }'
```

#### 运行时注册工具（通过 module:function 路径）

```bash
curl -X POST http://localhost:8000/tools \
  -H "Content-Type: application/json" \
  -d '{
    "name": "my_tool",
    "description": "...",
    "parameters": {"type": "object", "properties": {...}},
    "module_path": "my_package.my_module:my_function"
  }'
```

#### Skills

```bash
# 列出所有 skill
curl http://localhost:8000/skills

# 搜索
curl "http://localhost:8000/skills/search?q=git"

# 扫描目录
curl -X POST http://localhost:8000/skills/scan \
  -H "Content-Type: application/json" \
  -d '{"paths": ["/path/to/skills"]}'

# 注册为 tool（让 Agent 可调）
curl -X POST http://localhost:8000/skills/git-commit/as-tool
```

#### MCP

```bash
# 注册 MCP 服务器
curl -X POST http://localhost:8000/mcp/tools \
  -H "Content-Type: application/json" \
  -d '{"server_path": "/path/to/mcp_server.py"}'

# 列出所有会话
curl http://localhost:8000/mcp/sessions

# 单个会话详情
curl http://localhost:8000/mcp/sessions//path/to/mcp_server.py

# 关闭会话
curl -X DELETE http://localhost:8000/mcp/sessions//path/to/mcp_server.py

# 关闭所有
curl -X DELETE http://localhost:8000/mcp/sessions
```

#### 重新加载 Agent

`POST /agents/{name}/reload` —— 强制重建 system prompt + 工具列表。

## API 参考

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/health` | 健康检查 + 已注册 Agent/工具数量 |
| GET | `/agents` | 列出所有 Agent（按 UUID 去重） |
| GET | `/agents/{name_or_uuid}` | 取单个 Agent 元信息 |
| POST | `/agents` | 运行时注册 Agent |
| GET | `/agents/{name_or_uuid}/tools` | 列出 Agent 可用工具 |
| POST | `/agents/{name_or_uuid}/chat` | 与 Agent 对话（OpenAI 风格 + 流式 SSE） |
| POST | `/agents/{name_or_uuid}/reload` | 重新加载 Agent |
| GET | `/tools` | 列出所有已注册工具 |
| POST | `/tools` | 运行时注册工具（module:function 路径） |
| GET | `/skills` | 列出所有 Skill |
| GET | `/skills/search?q=...` | 关键词搜索 Skill |
| GET | `/skills/{name}` | 单个 Skill 详情 |
| POST | `/skills/scan` | 扫描目录注册 Skill |
| POST | `/skills/register` | 注册单个 Skill 目录 |
| DELETE | `/skills/{name}` | 取消注册 Skill |
| POST | `/skills/{name}/reload` | 重载 SKILL.md |
| POST | `/skills/{name}/as-tool` | 注册 Skill 为可调 Tool |
| DELETE | `/skills/{name}/as-tool` | 取消 Skill-as-tool |
| POST | `/mcp/tools` | 注册 MCP 服务器 |
| GET | `/mcp/sessions` | 列出所有 MCP 会话 |
| GET | `/mcp/sessions/{server_path}` | 单个会话详情 |
| DELETE | `/mcp/sessions` | 关闭所有会话 |
| DELETE | `/mcp/sessions/{server_path}` | 关闭单个会话 |
| POST | `/mcp/health-check/start` | 启动会话池健康检查 |
| POST | `/mcp/health-check/stop` | 停止会话池健康检查 |

自动生成的 OpenAPI 文档：`http://localhost:8000/docs`（Swagger UI）/ `/redoc`。

## 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `AGENTS_CONFIG` | `examples/api/agents_config.py` | 启动时 import 的脚本路径；设为空字符串跳过加载 |

## 测试

```bash
uv run pytest tests/test_api.py -v
```

测试用两个本地 mock HTTP server（OpenAI + Anthropic）模拟真实 wire 协议，让 Agent 走完
`transport → SSE 解析 → tool_call 抽取 → out 事件链` 全链路，再验证 HTTP 端点是否正确分发。

## 与 dumplingsAI 的关系

| 层级 | 文件 | 角色 |
|------|------|------|
| 框架核心 | `Dumplings/` | LLM Transport / Agent 注册 / 工具系统 |
| HTTP 扩展层 | `api/`（本目录） | 把框架能力暴露为 HTTP API |

`api/` 通过 `import dumplingsAI` 使用框架能力，**从不**修改 `Dumplings/` 子模块。

## 限制

1. **并发**：`conversation_with_tool` 是同步阻塞函数（含 HTTP 请求 + 工具执行），会阻塞 event loop。
   - 短期：`--workers N`（多 worker 进程）
   - 长期：用 `aconversation_with_tool`（框架已有）+ 改 async 路由
2. **鉴权**：当前无 auth，建议在 nginx / API gateway 层加。
3. **运行时注册 Agent** 通过 `type()` 动态构造类，没有 `__init_subclass__` 钩子，
   所以 `@builtin_tool` 子类覆写不会自动 promote——运行时注册的 Agent 只能用基类内建工具。
   需要内建工具请用 `agents_config.py` 写静态类。
4. **运行时注册工具** 需要函数已经是 importable 的（lambda / 内嵌函数不行）。

## 覆盖度

完整覆盖 dumplingsAI `__all__` 18 个公开 API 的 18/18 + Agent / 工具方法的全套常用子集。
详见 `tests/test_api.py`（25 个测试）。