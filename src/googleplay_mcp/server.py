"""FastMCP server 实例创建和 tool 注册."""

from __future__ import annotations

from typing import TYPE_CHECKING

from mcp.server.fastmcp import FastMCP

if TYPE_CHECKING:
    from googleplay_mcp.config import AppConfig


def create_server(config: AppConfig) -> FastMCP:
    """创建并配置 MCP server."""
    mcp = FastMCP(
        "Google Play MCP",
        instructions=(
            "Google Play 后台数据查询服务。"
            "提供 Vitals 指标 (崩溃率、ANR 率、慢启动等)、"
            "用户评论、购买验证、订阅管理、财务报告等查询能力。"
            "大部分 tool 需要 package_name 参数，可通过环境变量 GOOGLE_PLAY_PACKAGE_NAME 设置默认值。"
        ),
        host=config.server.host,
        port=config.server.port,
    )

    from googleplay_mcp.tools import register_all_tools

    register_all_tools(mcp, config)

    return mcp
