"""注册所有 MCP tools."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from googleplay_mcp.config import AppConfig


def register_all_tools(mcp: FastMCP, config: AppConfig) -> None:
    """注册所有 Google Play tools 到 MCP server."""
    from googleplay_mcp.tools.reporting import register_reporting_tools
    from googleplay_mcp.tools.reviews import register_reviews_tools
    from googleplay_mcp.tools.purchases import register_purchases_tools
    from googleplay_mcp.tools.monetization import register_monetization_tools
    from googleplay_mcp.tools.orders import register_orders_tools
    from googleplay_mcp.tools.reports import register_reports_tools

    register_reporting_tools(mcp, config)
    register_reviews_tools(mcp, config)
    register_purchases_tools(mcp, config)
    register_monetization_tools(mcp, config)
    register_orders_tools(mcp, config)
    register_reports_tools(mcp, config)
