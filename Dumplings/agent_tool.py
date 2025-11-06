from loguru import logger #配置日志
logger.add("logs/app.log", rotation="500 MB", retention="10 days", compression="zip")
from functools import wraps
from typing import List, Union, Optional


class tool:
    """工具注册管理器"""

    def __init__(self):
        self._tools = {}  # 存储工具信息
        self._agent_permissions = {}  # 存储agent权限
        self._uuid_to_name = {} #转换name与uuid

    def register_agent_uuid(self, uuid: str, name: str):
        """注册 agent 的 uuid 和 name 映射"""
        self._uuid_to_name[uuid] = name

    def register_tool(self,
                      allowed_agents: Union[str, List[str]] = None,
                      description: str = "",
                      name: Optional[str] = None):
        """
        工具注册装饰器

        Args:
            allowed_agents: 允许使用此工具的agent名称或列表，None表示所有agent都可以使用
            description: 工具方法简介
            name: 工具名称，如果不指定则使用方法名
        """

        def decorator(func):
            tool_name = name or func.__name__

            # 处理允许的agents列表
            if allowed_agents is None:
                permitted_agents = None  # None表示无限制
            elif isinstance(allowed_agents, str):
                permitted_agents = [allowed_agents]
            else:
                permitted_agents = list(allowed_agents)

            # 注册工具信息
            self._tools[tool_name] = {
                'function': func,
                'allowed_agents': permitted_agents,
                'description': description,
                'name': tool_name
            }

            logger.info(str({
                'function': func,
                'allowed_agents': permitted_agents,
                'description': description,
                'name': tool_name
            }))

            @wraps(func)
            def wrapper(*args, **kwargs):
                return func(*args, **kwargs)

            return wrapper

        return decorator

    def check_permission(self, agent_name: str, tool_name: str) -> bool:
        """检查 agent 是否有权限使用指定工具，支持 uuid 自动识别"""
        if tool_name not in self._tools:
            return False

        # 如果 agent_name 是 uuid，自动转换为 name
        try:
            logger.info("成功转换"+agent_name+" to "+self._uuid_to_name[agent_name])
            agent_name = self._uuid_to_name[agent_name]
        except:
            logger.info("传入name无需转换")

        tool_info = self._tools[tool_name]
        allowed_agents = tool_info['allowed_agents']

        if allowed_agents is None:
            return True

        return agent_name in allowed_agents

    def get_tool_info(self, tool_name: str) -> Optional[dict]:
        """获取工具信息"""
        return self._tools.get(tool_name)

    def list_tools(self) -> dict:
        """列出所有注册的工具"""
        return {name: {
            'description': info['description'],
            'allowed_agents': info['allowed_agents']
        } for name, info in self._tools.items()}


# 创建全局工具注册实例
tool_registry = tool()