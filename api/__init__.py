"""
AI Company - 把 dumplingsAI 暴露为 HTTP API 的 FastAPI 扩展层。

启动方式::

    # 方式 1：直接启动
    uvicorn api.app:app --reload

    # 方式 2：用 ai_company 提供的 CLI（如果有）
    uv run python -m ai_company

环境变量::

    AGENTS_CONFIG    指定用户自定义的 agent 注册脚本（默认 examples/api/agents_config.py）
                    该脚本会被自动 import，等同于在 main.py 里写 @register_agent。
                    设为空字符串则不加载任何 agent。

设计原则：

1. **零侵入**：dumplingsAI 子包完全不变；本目录是 *纯扩展*，依赖 dumplingsAI 但不修改它。
2. **配置驱动**：业务方通过写一个 ``agents_config.py`` 即可暴露自己的 Agent，不需要碰本目录代码。
3. **OpenAI 兼容**：``POST /v1/agents/{name}/chat`` 的请求/响应尽量对齐 OpenAI Chat Completions API，
   让现有 OpenAI 客户端（curl / openai-python / 任何 OpenAI SDK）零改动接入。
"""

__version__ = "0.1.0"