"""购买验证 + 退款查询 tools."""

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


def register_purchases_tools(mcp: FastMCP, config: AppConfig) -> None:
    """注册购买相关 tools."""

    # TODO: 暂时屏蔽，需要真实购买数据
    # @mcp.tool(name="googleplay_purchases_product_get")
    def purchases_product_get(
        product_id: str,
        token: str,
        package_name: str = "",
    ) -> dict:
        """验证应用内商品购买, 获取购买状态详情。

        Args:
            product_id: 应用内商品 ID (SKU)
            token: 购买时收到的 purchase token
            package_name: 应用包名, 留空使用默认配置
        """
        pkg = _resolve_package(config, package_name or None)
        if not pkg:
            return error("需要提供 package_name 或设置 GOOGLE_PLAY_PACKAGE_NAME")
        try:
            client = get_publisher_client(config)
            result = (
                client.purchases()
                .products()
                .get(packageName=pkg, productId=product_id, token=token)
                .execute()
            )
            return success(result)
        except HttpError as e:
            return handle_google_error(e)

    # TODO: 暂时屏蔽写入接口
    # @mcp.tool(name="googleplay_purchases_product_acknowledge")
    def purchases_product_acknowledge(
        product_id: str,
        token: str,
        package_name: str = "",
    ) -> dict:
        """确认应用内商品购买 (acknowledge)。

        Args:
            product_id: 应用内商品 ID (SKU)
            token: 购买时收到的 purchase token
            package_name: 应用包名, 留空使用默认配置
        """
        pkg = _resolve_package(config, package_name or None)
        if not pkg:
            return error("需要提供 package_name 或设置 GOOGLE_PLAY_PACKAGE_NAME")
        try:
            client = get_publisher_client(config)
            client.purchases().products().acknowledge(
                packageName=pkg, productId=product_id, token=token
            ).execute()
            return success({"status": "acknowledged"}, "购买确认成功")
        except HttpError as e:
            return handle_google_error(e)

    # TODO: 暂时屏蔽，需要真实购买数据
    # @mcp.tool(name="googleplay_purchases_subscription_get")
    def purchases_subscription_get(
        subscription_id: str,
        token: str,
        package_name: str = "",
    ) -> dict:
        """验证订阅购买状态 (v1 API)。

        Args:
            subscription_id: 订阅 ID
            token: 购买时收到的 purchase token
            package_name: 应用包名, 留空使用默认配置
        """
        pkg = _resolve_package(config, package_name or None)
        if not pkg:
            return error("需要提供 package_name 或设置 GOOGLE_PLAY_PACKAGE_NAME")
        try:
            client = get_publisher_client(config)
            result = (
                client.purchases()
                .subscriptions()
                .get(packageName=pkg, subscriptionId=subscription_id, token=token)
                .execute()
            )
            return success(result)
        except HttpError as e:
            return handle_google_error(e)

    # TODO: 暂时屏蔽，需要真实购买数据
    # @mcp.tool(name="googleplay_purchases_subscription_v2_get")
    def purchases_subscription_v2_get(
        token: str,
        package_name: str = "",
    ) -> dict:
        """验证订阅购买状态 (v2 API, 推荐使用)。返回更详细的订阅状态信息。

        Args:
            token: 购买时收到的 purchase token
            package_name: 应用包名, 留空使用默认配置
        """
        pkg = _resolve_package(config, package_name or None)
        if not pkg:
            return error("需要提供 package_name 或设置 GOOGLE_PLAY_PACKAGE_NAME")
        try:
            client = get_publisher_client(config)
            result = (
                client.purchases()
                .subscriptionsv2()
                .get(packageName=pkg, token=token)
                .execute()
            )
            return success(result)
        except HttpError as e:
            return handle_google_error(e)

    @mcp.tool(name="googleplay_purchases_voided_list")
    def purchases_voided_list(
        package_name: str = "",
        start_time: str = "",
        end_time: str = "",
        max_results: int = 100,
        token: str = "",
        voided_source: int = 0,
        type_filter: int = 0,
    ) -> dict:
        """列出退款和撤销的购买记录 (最近 30 天)。

        Args:
            package_name: 应用包名, 留空使用默认配置
            start_time: 起始时间 (毫秒时间戳)
            end_time: 结束时间 (毫秒时间戳)
            max_results: 最大返回数量, 默认 100
            token: 分页 token
            voided_source: 退款来源 (0=全部, 1=开发者, 2=Google, 3=用户)
            type_filter: 类型过滤 (0=全部, 1=应用内商品, 2=订阅)
        """
        pkg = _resolve_package(config, package_name or None)
        if not pkg:
            return error("需要提供 package_name 或设置 GOOGLE_PLAY_PACKAGE_NAME")
        try:
            client = get_publisher_client(config)
            kwargs: dict = {"packageName": pkg, "maxResults": max_results}
            if start_time:
                kwargs["startTime"] = start_time
            if end_time:
                kwargs["endTime"] = end_time
            if token:
                kwargs["token"] = token
            if voided_source:
                kwargs["voidedSource"] = voided_source
            if type_filter:
                kwargs["type"] = type_filter

            result = (
                client.purchases().voidedpurchases().list(**kwargs).execute()
            )
            items = result.get("voidedPurchases", [])
            return success(result, f"找到 {len(items)} 条退款记录")
        except HttpError as e:
            return handle_google_error(e)
