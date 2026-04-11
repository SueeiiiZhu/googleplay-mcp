"""订阅和应用内商品配置查询 tools."""

from __future__ import annotations

from typing import TYPE_CHECKING

from googleapiclient.errors import HttpError

from googleplay_mcp.auth import get_publisher_client
from googleplay_mcp.utils.errors import handle_google_error
from googleplay_mcp.utils.response import error, success

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from googleplay_mcp.config import AppConfig


def _resolve_package(config: AppConfig, package_name: str | None) -> str | None:
    return package_name or config.google.default_package_name


def register_monetization_tools(mcp: FastMCP, config: AppConfig) -> None:
    """注册商品化查询 tools."""

    @mcp.tool(name="googleplay_subscriptions_list")
    def subscriptions_list(
        package_name: str = "",
        page_size: int = 100,
        page_token: str = "",
    ) -> dict:
        """列出应用的所有订阅配置。

        Args:
            package_name: 应用包名, 留空使用默认配置
            page_size: 每页数量, 默认 100
            page_token: 分页 token
        """
        pkg = _resolve_package(config, package_name or None)
        if not pkg:
            return error("需要提供 package_name 或设置 GOOGLE_PLAY_PACKAGE_NAME")
        try:
            client = get_publisher_client(config)
            kwargs: dict = {"packageName": pkg, "pageSize": page_size}
            if page_token:
                kwargs["pageToken"] = page_token

            result = (
                client.monetization().subscriptions().list(**kwargs).execute()
            )
            subs = result.get("subscriptions", [])
            return success(result, f"找到 {len(subs)} 个订阅")
        except HttpError as e:
            return handle_google_error(e)

    # TODO: 暂时屏蔽，需要真实购买数据
    # @mcp.tool(name="googleplay_subscriptions_get")
    def subscriptions_get(
        product_id: str,
        package_name: str = "",
    ) -> dict:
        """获取单个订阅的配置详情。

        Args:
            product_id: 订阅商品 ID
            package_name: 应用包名, 留空使用默认配置
        """
        pkg = _resolve_package(config, package_name or None)
        if not pkg:
            return error("需要提供 package_name 或设置 GOOGLE_PLAY_PACKAGE_NAME")
        try:
            client = get_publisher_client(config)
            result = (
                client.monetization()
                .subscriptions()
                .get(packageName=pkg, productId=product_id)
                .execute()
            )
            return success(result)
        except HttpError as e:
            return handle_google_error(e)

    @mcp.tool(name="googleplay_inappproducts_list")
    def inappproducts_list(
        package_name: str = "",
        max_results: int = 100,
        start_index: int = 0,
        token: str = "",
    ) -> dict:
        """列出应用的所有应用内商品。

        Args:
            package_name: 应用包名, 留空使用默认配置
            max_results: 最大返回数量, 默认 100
            start_index: 起始索引
            token: 分页 token
        """
        pkg = _resolve_package(config, package_name or None)
        if not pkg:
            return error("需要提供 package_name 或设置 GOOGLE_PLAY_PACKAGE_NAME")
        try:
            client = get_publisher_client(config)
            kwargs: dict = {"packageName": pkg, "maxResults": max_results}
            if start_index:
                kwargs["startIndex"] = start_index
            if token:
                kwargs["token"] = token

            result = client.inappproducts().list(**kwargs).execute()
            products = result.get("inappproduct", [])
            return success(result, f"找到 {len(products)} 个应用内商品")
        except HttpError as e:
            return handle_google_error(e)

    @mcp.tool(name="googleplay_inappproducts_get")
    def inappproducts_get(
        sku: str,
        package_name: str = "",
    ) -> dict:
        """获取单个应用内商品的详情。

        Args:
            sku: 商品 ID (SKU)
            package_name: 应用包名, 留空使用默认配置
        """
        pkg = _resolve_package(config, package_name or None)
        if not pkg:
            return error("需要提供 package_name 或设置 GOOGLE_PLAY_PACKAGE_NAME")
        try:
            client = get_publisher_client(config)
            result = (
                client.inappproducts()
                .get(packageName=pkg, sku=sku)
                .execute()
            )
            return success(result)
        except HttpError as e:
            return handle_google_error(e)
