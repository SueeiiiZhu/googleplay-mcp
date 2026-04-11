"""订单查询 tools."""

from __future__ import annotations

from typing import TYPE_CHECKING

from googleapiclient.errors import HttpError

from googleplay_mcp.auth import get_publisher_client
from googleplay_mcp.utils.errors import handle_google_error
from googleplay_mcp.utils.response import error, success

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from googleplay_mcp.config import AppConfig


def register_orders_tools(mcp: FastMCP, config: AppConfig) -> None:
    """注册订单查询 tools."""

    # TODO: 暂时屏蔽，需要真实购买数据
    # @mcp.tool(name="googleplay_orders_get")
    def orders_get(
        order_id: str,
        package_name: str = "",
    ) -> dict:
        """获取订单详情 (含费用、税金、退款信息)。

        Args:
            order_id: 订单 ID
            package_name: 应用包名, 留空使用默认配置
        """
        pkg = package_name or config.google.default_package_name
        if not pkg:
            return error("需要提供 package_name 或设置 GOOGLE_PLAY_PACKAGE_NAME")
        try:
            client = get_publisher_client(config)
            result = (
                client.orders()
                .get(packageName=pkg, orderId=order_id)
                .execute()
            )
            return success(result)
        except HttpError as e:
            return handle_google_error(e)
