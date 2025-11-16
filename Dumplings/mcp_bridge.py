import asyncio
import os
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from .agent_tool import tool_registry
from loguru import logger

async def register_mcp_tools(server_script_path: str):
    """一键把 MCP 服务器所有 tool 注册成 Dumplings  XML 工具"""
    cmd = "python" if server_script_path.endswith(".py") else "node"
    params = StdioServerParameters(command=cmd, args=[server_script_path], env=None)

    async with stdio_client(params) as (reader, writer), \
               ClientSession(reader, writer) as session:
        await session.initialize()
        tools = (await session.list_tools()).tools
        logger.info(f"MCP 共 {len(tools)} 个工具待注册")

        for tool in tools:
            name = tool.name
            desc = tool.description or ""
            schema = tool.inputSchema

            # 闭包捕获当前 session/name/schema
            def make_func(tool_name=name, sess=session):
                def sync_xml_wrapper(xml_block: str) -> str:
                    from bs4 import BeautifulSoup
                    soup = BeautifulSoup(xml_block, "xml")
                    root = soup.find(tool_name)
                    if root is None:
                        return f"<error>缺少 {tool_name} 根标签</error>"
                    # 构造 JSON 参数
                    args = {child.name: child.text for child in root.find_all()}
                    # 异步转同步
                    result = asyncio.run(sess.call_tool(tool_name, args))
                    return result.content      # 文本结果
                return sync_xml_wrapper

            tool_registry.register_tool(
                name=name,
                description=desc,
                allowed_agents=None          # 开放给所有 agent
            )(make_func())

            logger.info(f"已注册 XML 工具 <{name}>")

def connect_and_register(server_script_path: str):
    """同步入口，直接调"""
    if not os.path.isfile(server_script_path):
        raise FileNotFoundError(server_script_path)
    asyncio.run(register_mcp_tools(server_script_path))