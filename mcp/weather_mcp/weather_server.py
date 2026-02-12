#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
天气 MCP 服务器 - 伪实现版本

无论输入什么地址，始终返回温暖的天气
"""

from mcp.server import Server
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types


# 1. 创建服务器实例
server = Server("weather-server")


# 2. 定义工具列表
@server.list_tools()
async def handle_list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name="get_weather",
            description="获取指定位置的天气信息（伪实现：始终返回温暖）",
            inputSchema={
                "type": "object",
                "properties": {
                    "location": {"type": "string", "description": "位置/地址"}
                },
                "required": ["location"]
            }
        )
    ]


# 3. 定义工具调用处理
@server.call_tool()
async def handle_call_tool(
    name: str,
    arguments: dict | None
) -> list[types.TextContent]:
    if name == "get_weather":
        location = arguments.get("location", "未知位置")

        # 伪实现：始终返回温暖
        return [
            types.TextContent(
                type="text",
                text=f"{location} 天气：温度 25°C，天气温暖，湿度 60%"
            )
        ]

    raise ValueError(f"未知工具: {name}")


# 4. 启动服务器
async def main():
    async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="weather-server",
                server_version="1.0.0"
            )
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())