"""
FastAPI 应用工厂 + lifespan。

启动顺序：

1. 构造 FastAPI app
2. 注册路由
3. 启动时（lifespan）按需加载用户的 ``agents_config.py``：
   - AGENTS_CONFIG 环境变量指定脚本路径（默认 examples/api/agents_config.py）
   - import 脚本即触发 @register_agent 装饰器把 Agent 写入 dumplingsAI.agent_list

为什么用 import 而不是 exec / runpy？

- import 会触发模块级副作用（@register_agent），但不会污染用户的全局命名空间
- 错误会以 ImportError 形式抛出，启动失败能立刻看到
- 多次 reload 不会重复注册（dumplingsAI 用 uuid/名称双键去重）
"""

from __future__ import annotations

import importlib.util
import logging
import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional

from fastapi import FastAPI

import dumplingsAI

from .routes import agents, health, mcp, skills, tools

logger = logging.getLogger(__name__)

DEFAULT_AGENTS_CONFIG = "examples/api/agents_config.py"


def _load_agents_config(app: FastAPI) -> Optional[str]:
    """
    按 AGENTS_CONFIG 环境变量加载用户的 Agent 注册脚本。

    Returns:
        加载的脚本路径；若 AGENTS_CONFIG="" 或文件不存在，返回 None。
    """
    path_str = os.getenv("AGENTS_CONFIG", DEFAULT_AGENTS_CONFIG)
    if not path_str:
        return None
    path = Path(path_str)
    if not path.is_absolute():
        # 相对路径相对 cwd；常见情况是 uvicorn 从 AI_Company/ 启动
        path = Path.cwd() / path
    if not path.exists():
        logger.warning("AGENTS_CONFIG 指向的文件不存在：%s（跳过加载）", path)
        return None

    module_name = f"_ai_company_user_agents_{path.stem}"
    spec = importlib.util.spec_from_file_location(module_name, str(path))
    if spec is None or spec.loader is None:
        logger.warning("无法加载 AGENTS_CONFIG：%s", path)
        return None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    logger.info("AGENTS_CONFIG 已加载：%s（已注册 %d 个 Agent）", path, len(dumplingsAI.agent_list))
    return str(path)


@asynccontextmanager
async def lifespan(app: FastAPI):
    _load_agents_config(app)
    yield


def create_app() -> FastAPI:
    """构造 FastAPI 应用实例（便于测试时传自定义 lifespan / 配置）"""
    app = FastAPI(
        title="AI Company API",
        description=(
            "把 dumplingsAI 框架暴露为 HTTP API。"
            "请求 / 响应尽量对齐 OpenAI Chat Completions，方便现有客户端零改动接入。"
        ),
        version=dumplingsAI.__version__,
        lifespan=lifespan,
    )
    app.include_router(health.router)
    app.include_router(agents.router)
    app.include_router(tools.router)
    app.include_router(skills.router)
    app.include_router(mcp.router)
    return app


# 模块级 app 实例：``uvicorn api.app:app --reload`` 直接用
app = create_app()