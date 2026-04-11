"""GCS 财务/销售报告下载 tools."""

from __future__ import annotations

import csv
import io
from typing import TYPE_CHECKING

from googleplay_mcp.auth import get_credentials
from googleplay_mcp.utils.response import error, success

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from googleplay_mcp.config import AppConfig


def register_reports_tools(mcp: FastMCP, config: AppConfig) -> None:
    """注册 GCS 报告下载 tools."""

    @mcp.tool(name="googleplay_reports_list_files")
    def reports_list_files(
        report_type: str = "earnings",
        bucket: str = "",
        prefix: str = "",
        max_results: int = 50,
    ) -> dict:
        """列出 Google Play 报告 bucket 中的报告文件。

        Args:
            report_type: 报告类型 - earnings (收入), sales (销售), installs (安装), crashes (崩溃), reviews (评论)
            bucket: GCS bucket 名称, 留空使用默认配置
            prefix: 文件前缀过滤 (如 '202401' 过滤 2024 年 1 月)
            max_results: 最大返回文件数, 默认 50
        """
        bucket_name = bucket or config.google.report_bucket
        if not bucket_name:
            return error(
                "需要提供 bucket 名称或设置 GOOGLE_PLAY_REPORT_BUCKET。\n"
                "bucket 格式通常为 pubsite_prod_rev_XXXXXXXXXX，\n"
                "可在 Google Play Console → 下载报告 → 复制 Cloud Storage URI 获取。"
            )
        try:
            from google.cloud import storage

            credentials = get_credentials(config)
            client = storage.Client(credentials=credentials, project=credentials.project_id)
            bucket_obj = client.bucket(bucket_name)

            type_prefix_map = {
                "earnings": "earnings/",
                "sales": "sales/",
                "installs": "stats/installs/",
                "crashes": "stats/crashes/",
                "reviews": "reviews/",
            }
            full_prefix = type_prefix_map.get(report_type, f"{report_type}/")
            if prefix:
                full_prefix += prefix

            blobs = list(bucket_obj.list_blobs(prefix=full_prefix, max_results=max_results))
            files = [
                {
                    "name": blob.name,
                    "size": blob.size,
                    "updated": str(blob.updated),
                }
                for blob in blobs
            ]
            return success(files, f"找到 {len(files)} 个报告文件")
        except Exception as e:
            return error(f"列出报告文件失败: {e}")

    @mcp.tool(name="googleplay_reports_download")
    def reports_download(
        file_path: str,
        bucket: str = "",
        max_rows: int = 500,
    ) -> dict:
        """下载并解析 Google Play 报告文件 (CSV 格式)。

        Args:
            file_path: 报告文件路径 (从 reports_list_files 获取的 name 字段)
            bucket: GCS bucket 名称, 留空使用默认配置
            max_rows: 最大返回行数, 默认 500 (防止超大文件)
        """
        bucket_name = bucket or config.google.report_bucket
        if not bucket_name:
            return error("需要提供 bucket 名称或设置 GOOGLE_PLAY_REPORT_BUCKET")
        try:
            from google.cloud import storage

            credentials = get_credentials(config)
            client = storage.Client(credentials=credentials, project=credentials.project_id)
            bucket_obj = client.bucket(bucket_name)
            blob = bucket_obj.blob(file_path)

            content = blob.download_as_text(encoding="utf-16")

            reader = csv.DictReader(io.StringIO(content))
            rows = []
            for i, row in enumerate(reader):
                if i >= max_rows:
                    break
                rows.append(dict(row))

            total_hint = f"(显示前 {max_rows} 行)" if len(rows) == max_rows else ""
            return success(
                {"headers": reader.fieldnames, "rows": rows, "row_count": len(rows)},
                f"解析 {file_path} 得到 {len(rows)} 行数据 {total_hint}",
            )
        except Exception as e:
            return error(f"下载报告失败: {e}")
