"""评论相关 tools — 列表、详情、回复."""

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


def register_reviews_tools(mcp: FastMCP, config: AppConfig) -> None:
    """注册评论相关 tools."""

    @mcp.tool(name="googleplay_reviews_list")
    def reviews_list(
        package_name: str = "",
        max_results: int = 100,
        start_index: int = 0,
        token: str = "",
        translation_language: str = "",
    ) -> dict:
        """获取应用的用户评论列表 (最近一周的评论)。

        Args:
            package_name: 应用包名, 留空使用默认配置
            max_results: 最大返回数量, 默认 100
            start_index: 起始索引
            token: 分页 token
            translation_language: 翻译目标语言 (BCP-47 格式, 如 zh-CN)
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
            if translation_language:
                kwargs["translationLanguage"] = translation_language

            result = client.reviews().list(**kwargs).execute()
            reviews = result.get("reviews", [])
            return success(result, f"获取到 {len(reviews)} 条评论")
        except HttpError as e:
            return handle_google_error(e)

    @mcp.tool(name="googleplay_reviews_get")
    def reviews_get(
        review_id: str,
        package_name: str = "",
        translation_language: str = "",
    ) -> dict:
        """获取单条评论详情。

        Args:
            review_id: 评论 ID
            package_name: 应用包名, 留空使用默认配置
            translation_language: 翻译目标语言 (BCP-47 格式)
        """
        pkg = _resolve_package(config, package_name or None)
        if not pkg:
            return error("需要提供 package_name 或设置 GOOGLE_PLAY_PACKAGE_NAME")
        try:
            client = get_publisher_client(config)
            kwargs: dict = {"packageName": pkg, "reviewId": review_id}
            if translation_language:
                kwargs["translationLanguage"] = translation_language

            result = client.reviews().get(**kwargs).execute()
            return success(result)
        except HttpError as e:
            return handle_google_error(e)

    # TODO: 暂时屏蔽写入接口
    # @mcp.tool(name="googleplay_reviews_reply")
    def reviews_reply(
        review_id: str,
        reply_text: str,
        package_name: str = "",
    ) -> dict:
        """回复用户评论。

        Args:
            review_id: 评论 ID
            reply_text: 回复内容文本
            package_name: 应用包名, 留空使用默认配置
        """
        pkg = _resolve_package(config, package_name or None)
        if not pkg:
            return error("需要提供 package_name 或设置 GOOGLE_PLAY_PACKAGE_NAME")
        try:
            client = get_publisher_client(config)
            body = {"replyText": reply_text}
            result = (
                client.reviews()
                .reply(packageName=pkg, reviewId=review_id, body=body)
                .execute()
            )
            return success(result, "回复成功")
        except HttpError as e:
            return handle_google_error(e)
