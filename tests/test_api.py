"""
API 扩展层的端到端集成测试。

策略：起两个本地 mock HTTP server（OpenAI 协议 + Anthropic 协议），
返回符合各自规范的 SSE 流，让 Agent 走完整 transport → SSE 解析 →
tool_call 抽取 → out 事件链。验证的不是 mock，而是真实 wire 协议。

这样能捕获：

- llm_transport.py 的 SSE 解析逻辑（之前出现过 tool_use 块丢失 bug）
- api/deps.py 的 stream_agent_chat（流式分发）
- api/routes/agents.py 的 chat endpoint（流式/非流式两条路径）
- 整个 OpenAI 兼容请求/响应形状

跑前会自动加载 examples/api/agents_config.py，并把 agent 的 api_provider
临时指向 mock server URL（用 fixture 的 monkeypatch 还原，不污染其他测试）。
"""

from __future__ import annotations

import importlib.util
import json
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Iterator, Optional

import pytest

# 让 tests/ 能 import 根目录的 api/ 包
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))


# ---------------------------------------------------------------------------
# Mock HTTP servers —— 假装是 OpenAI / Anthropic 真实 API
# ---------------------------------------------------------------------------

def _make_openai_sse_chunks(text: str = "hello world", tool_calls: Optional[list] = None) -> list:
    """构造 OpenAI Chat Completions 的 SSE 流（与 dumplingsAI.llm_transport.HttpxOpenAITransport 期望的格式一致）"""
    chunks = []
    chunks.append({
        "id": "chatcmpl-test",
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": "test-model",
        "choices": [{"index": 0, "delta": {"role": "assistant", "content": ""}, "finish_reason": None}],
    })
    for i, ch in enumerate(text):
        chunks.append({
            "id": "chatcmpl-test",
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": "test-model",
            "choices": [{"index": 0, "delta": {"content": ch}, "finish_reason": None}],
        })
    if tool_calls:
        for i, tc in enumerate(tool_calls):
            chunks.append({
                "id": "chatcmpl-test",
                "object": "chat.completion.chunk",
                "created": int(time.time()),
                "model": "test-model",
                "choices": [{
                    "index": 0,
                    "delta": {"tool_calls": [{
                        "index": i,
                        "id": tc["id"],
                        "type": "function",
                        "function": {"name": tc["name"], "arguments": json.dumps(tc["arguments"])},
                    }]},
                    "finish_reason": None,
                }],
            })
    chunks.append({
        "id": "chatcmpl-test",
        "object": "chat.completion.chunk",
        "created": int(time.time()),
        "model": "test-model",
        "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
    })
    return chunks


def _make_anthropic_sse_events(text: str = "hello world") -> list:
    """构造 Anthropic Messages API 的 SSE 流（与 dumplingsAI.llm_transport.HttpxAnthropicTransport 期望的格式一致）"""
    events = []
    events.append({
        "type": "message_start",
        "message": {
            "id": "msg-test",
            "type": "message",
            "role": "assistant",
            "content": [],
            "model": "test-model",
            "stop_reason": None,
            "usage": {"input_tokens": 5, "output_tokens": 0},
        },
    })
    events.append({
        "type": "content_block_start",
        "index": 0,
        "content_block": {"type": "text", "text": ""},
    })
    for ch in text:
        events.append({
            "type": "content_block_delta",
            "index": 0,
            "delta": {"type": "text_delta", "text": ch},
        })
    events.append({"type": "content_block_stop", "index": 0})
    events.append({
        "type": "message_delta",
        "delta": {"stop_reason": "end_turn"},
        "usage": {"output_tokens": len(text)},
    })
    events.append({"type": "message_stop"})
    return events


class _OpenAIMockHandler(BaseHTTPRequestHandler):
    """Mock OpenAI Chat Completions 端点（返回 SSE 流）"""

    # 类级可配置：默认 mock 返回内容
    response_text: str = "hello world"
    tool_calls: Optional[list] = None

    def do_POST(self):
        # 读 body 但不解析（mock 不关心 input）
        length = int(self.headers.get("Content-Length", 0))
        if length:
            self.rfile.read(length)

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()

        for chunk in _make_openai_sse_chunks(self.response_text, self.tool_calls):
            self.wfile.write(f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n".encode())
            self.wfile.flush()
        self.wfile.write(b"data: [DONE]\n\n")
        self.wfile.flush()

    def log_message(self, format, *args):  # noqa: A002
        pass  # 静默访问日志


class _AnthropicMockHandler(BaseHTTPRequestHandler):
    """Mock Anthropic Messages API 端点（返回 SSE 流）"""

    response_text: str = "hello from anthropic mock"

    def do_POST(self):
        length = int(self.headers.get("Content-Length", 0))
        if length:
            self.rfile.read(length)

        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()

        for ev in _make_anthropic_sse_events(self.response_text):
            self.wfile.write(f"event: {ev['type']}\n".encode())
            self.wfile.write(f"data: {json.dumps(ev, ensure_ascii=False)}\n\n".encode())
            self.wfile.flush()

    def log_message(self, format, *args):  # noqa: A002
        pass


def _start_mock_server(handler_cls) -> tuple[str, ThreadingHTTPServer]:
    """启动 ThreadingHTTPServer，监听 127.0.0.1 随机端口。返回 (base_url, server)。"""
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler_cls)
    base_url = f"http://127.0.0.1:{server.server_address[1]}"
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return base_url, server


# ---------------------------------------------------------------------------
# fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(scope="module")
def mock_urls():
    """启动 OpenAI + Anthropic mock server，配置 handlers 返回确定内容"""
    # 启动前先重置类变量，避免上一个 module 的污染
    _OpenAIMockHandler.response_text = "hello from openai mock"
    _AnthropicMockHandler.response_text = "hello from anthropic mock"

    openai_url, openai_server = _start_mock_server(_OpenAIMockHandler)
    anthropic_url, anthropic_server = _start_mock_server(_AnthropicMockHandler)

    yield {
        "openai_url": openai_url,
        "anthropic_url": anthropic_url,
    }

    openai_server.shutdown()
    openai_server.server_close()
    anthropic_server.shutdown()
    anthropic_server.server_close()


@pytest.fixture(scope="module")
def client(mock_urls):
    """
    构造 TestClient + 加载 examples/api/agents_config.py + 把 agent 的 api_provider
    指向 mock server URL（用类属性 monkey-patch，fixture 结束时会还原）。
    """
    # 1. 加载 agents_config（触发 @register_agent）
    config_path = Path(__file__).parent.parent / "examples" / "api" / "agents_config.py"
    spec = importlib.util.spec_from_file_location("_test_agents_config", config_path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)

    # 2. 把 agent 的 api_provider 指向 mock server（类属性）
    #    patch 完成后 yield，fixture 结束时会还原
    import dumplingsAI as _da

    openai_url = mock_urls["openai_url"]
    anthropic_url = mock_urls["anthropic_url"]

    # 找到我们刚注册的 demo / claude agent 类，存原 api_provider 用于还原
    originals = []
    for inst in _da.agent_list.values():
        cls = type(inst)
        if hasattr(cls, "api_provider"):
            originals.append((cls, "api_provider", cls.api_provider))
            if cls.__name__ == "APIDemoAgent":
                cls.api_provider = openai_url + "/v1/chat/completions"
                cls.model_name = "test-model"
                cls.api_key = "test-key"
            elif cls.__name__ == "APIClaudeAgent":
                cls.api_provider = anthropic_url
                cls.model_name = "test-model"
                cls.api_key = "test-key"

    # 关掉 _connectivity 后台线程（mock server 没法响应 GET-only ping）
    # _connectivity 是 daemon thread，pytest 退出时会自动回收

    # 3. 构造 FastAPI app
    from fastapi import FastAPI
    from api.routes import agents, health, mcp, skills, tools

    app = FastAPI(title="AI Company API (test)", version=_da.__version__)
    app.include_router(health.router)
    app.include_router(agents.router)
    app.include_router(tools.router)
    app.include_router(skills.router)
    app.include_router(mcp.router)

    from fastapi.testclient import TestClient
    yield TestClient(app)

    # 还原 api_provider
    for cls, attr, value in originals:
        setattr(cls, attr, value)


# ---------------------------------------------------------------------------
# tests —— health / agents 元信息 / tools 元信息
# ---------------------------------------------------------------------------

def test_health(client):
    rsp = client.get("/health")
    assert rsp.status_code == 200
    body = rsp.json()
    assert body["status"] == "ok"
    assert "version" in body
    assert body["n_agents"] >= 1
    assert body["n_tools"] >= 1


def test_list_agents(client):
    rsp = client.get("/agents")
    assert rsp.status_code == 200
    body = rsp.json()
    assert body["total"] >= 1
    names = {a["name"] for a in body["agents"]}
    assert "api_demo_agent" in names
    assert "api_claude_agent" in names


def test_get_agent_by_name(client):
    rsp = client.get("/agents/api_demo_agent")
    assert rsp.status_code == 200
    body = rsp.json()
    assert body["name"] == "api_demo_agent"
    assert body["uuid"]
    assert body["protocol"] in (None, "openai")


def test_get_agent_404(client):
    rsp = client.get("/agents/nonexistent_agent")
    assert rsp.status_code == 404
    assert "不存在" in rsp.json()["detail"]


def test_get_agent_claude(client):
    rsp = client.get("/agents/api_claude_agent")
    assert rsp.status_code == 200
    assert rsp.json()["protocol"] == "anthropic"


def test_get_agent_tools(client):
    rsp = client.get("/agents/api_demo_agent/tools")
    assert rsp.status_code == 200
    body = rsp.json()
    assert body["agent_name"] == "api_demo_agent"
    assert "echo" in body["tool_names"]


# ---------------------------------------------------------------------------
# tests —— chat：走真实 wire 协议（mock server 返回 SSE）
# ---------------------------------------------------------------------------

def test_chat_request_validation(client):
    rsp = client.post(
        "/agents/api_demo_agent/chat",
        json={"messages": []},
    )
    assert rsp.status_code == 422


def test_chat_no_user_message(client):
    rsp = client.post(
        "/agents/api_demo_agent/chat",
        json={"messages": [{"role": "system", "content": "你是助手"}]},
    )
    assert rsp.status_code == 400


def test_chat_non_stream_openai(client):
    """非流式 chat 走 OpenAI mock server"""
    rsp = client.post(
        "/agents/api_demo_agent/chat",
        json={"messages": [{"role": "user", "content": "hi"}]},
    )
    assert rsp.status_code == 200
    body = rsp.json()
    text = body["choices"][0]["message"]["content"]
    # mock 返回 "hello from openai mock"
    assert text == "hello from openai mock"
    assert body["agent_name"] == "api_demo_agent"


def test_chat_non_stream_anthropic(client):
    """非流式 chat 走 Anthropic mock server"""
    rsp = client.post(
        "/agents/api_claude_agent/chat",
        json={"messages": [{"role": "user", "content": "hi"}]},
    )
    assert rsp.status_code == 200
    body = rsp.json()
    text = body["choices"][0]["message"]["content"]
    assert text == "hello from anthropic mock"


def test_chat_stream_openai(client):
    """流式 chat 走 OpenAI mock server —— 验证 SSE 事件链路完整"""
    rsp = client.post(
        "/agents/api_demo_agent/chat",
        json={
            "messages": [{"role": "user", "content": "hi"}],
            "stream": True,
        },
    )
    assert rsp.status_code == 200
    assert rsp.headers["content-type"].startswith("text/event-stream")
    body = rsp.text
    # 应该有 text 增量 + done 收尾
    assert "data:" in body
    assert '"event": "text"' in body
    assert '"event": "done"' in body
    # 内容片段
    assert '"delta": "h"' in body or '"delta": "hello from openai mock"' in body


def test_chat_stream_anthropic(client):
    """流式 chat 走 Anthropic mock server"""
    rsp = client.post(
        "/agents/api_claude_agent/chat",
        json={
            "messages": [{"role": "user", "content": "hi"}],
            "stream": True,
        },
    )
    assert rsp.status_code == 200
    assert rsp.headers["content-type"].startswith("text/event-stream")
    body = rsp.text
    assert '"event": "text"' in body
    assert '"event": "done"' in body


# ---------------------------------------------------------------------------
# tests —— tools
# ---------------------------------------------------------------------------

def test_list_tools(client):
    rsp = client.get("/tools")
    assert rsp.status_code == 200
    body = rsp.json()
    assert body["total"] >= 1
    names = {t["name"] for t in body["tools"]}
    assert "echo" in names


def test_register_tool_runtime(client):
    rsp = client.post(
        "/tools",
        json={
            "name": "runtime_echo",
            "description": "runtime echo",
            "parameters": {"type": "object", "properties": {"x": {"type": "string"}}},
            "module_path": "examples.api.agents_config:echo",
        },
    )
    assert rsp.status_code == 200
    assert rsp.json()["status"] == "registered"


def test_register_tool_bad_module_path(client):
    rsp = client.post(
        "/tools",
        json={
            "name": "x",
            "description": "",
            "parameters": {},
            "module_path": "no_colon_here",
        },
    )
    assert rsp.status_code == 400


# ---------------------------------------------------------------------------
# tests —— Agent 运行时注册
# ---------------------------------------------------------------------------

def test_register_agent_runtime(client):
    rsp = client.post(
        "/agents",
        json={
            "name": "rt_agent",
            "description": "test",
            "protocol": "openai",
            "prompt": "x",
            "model_name": "test-model",
        },
    )
    assert rsp.status_code == 200
    body = rsp.json()
    assert body["name"] == "rt_agent"
    assert body["status"] == "registered"
    rsp2 = client.get("/agents/rt_agent")
    assert rsp2.status_code == 200


# ---------------------------------------------------------------------------
# tests —— Skill
# ---------------------------------------------------------------------------

def test_skills_list_empty(client):
    rsp = client.get("/skills")
    assert rsp.status_code == 200
    assert "skills" in rsp.json()


def test_skills_get_404(client):
    rsp = client.get("/skills/no_such_skill")
    assert rsp.status_code == 404


def test_skills_scan_unknown_path(client):
    rsp = client.post(
        "/skills/scan",
        json={"paths": ["/path/does/not/exist"]},
    )
    assert rsp.status_code == 200


# ---------------------------------------------------------------------------
# tests —— MCP
# ---------------------------------------------------------------------------

def test_mcp_sessions_list_empty(client):
    rsp = client.get("/mcp/sessions")
    assert rsp.status_code == 200
    assert rsp.json()["total"] == 0


def test_mcp_session_404(client):
    rsp = client.get("/mcp/sessions/no_such")
    assert rsp.status_code == 404


def test_mcp_register_path_not_found(client):
    rsp = client.post(
        "/mcp/tools",
        json={"server_path": "/no/such/path.py"},
    )
    assert rsp.status_code == 404


def test_mcp_close_all(client):
    rsp = client.delete("/mcp/sessions")
    assert rsp.status_code == 200


def test_mcp_health_check_start_stop(client):
    rsp = client.post("/mcp/health-check/start", json={"interval": 60})
    assert rsp.status_code == 200
    rsp2 = client.post("/mcp/health-check/stop")
    assert rsp2.status_code == 200


# ---------------------------------------------------------------------------
# tests —— reload
# ---------------------------------------------------------------------------

def test_reload_agent(client):
    rsp = client.post("/agents/api_demo_agent/reload")
    assert rsp.status_code == 200
    assert rsp.json()["agent"] == "api_demo_agent"