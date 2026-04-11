"""Google Play Developer Reporting API tools — vitals 指标查询 + 异常检测."""

from __future__ import annotations

from typing import TYPE_CHECKING

from googleapiclient.errors import HttpError

from googleplay_mcp.auth import get_reporting_service
from googleplay_mcp.utils.errors import handle_google_error
from googleplay_mcp.utils.response import error, success

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from googleplay_mcp.config import AppConfig


def _resolve_package(config: AppConfig, package_name: str | None) -> str | None:
    return package_name or config.google.default_package_name


# vitals 指标集列表: (metric_set_id, resource_name_id, 中文名, description, default_metrics)
# metric_set_id: 用于 service.vitals().xxx() 的小写名称
# resource_name_id: 用于 API resource name 的 camelCase 名称
_VITALS_METRIC_SETS = [
    ("anrrate", "anrRateMetricSet", "ANR 率",
     "查询应用的 ANR (Application Not Responding) 率指标",
     ["anrRate", "userPerceivedAnrRate", "distinctUsers"]),
    ("crashrate", "crashRateMetricSet", "崩溃率",
     "查询应用的崩溃率指标",
     ["crashRate", "userPerceivedCrashRate", "distinctUsers"]),
    ("slowstartrate", "slowStartRateMetricSet", "慢启动率",
     "查询应用的冷启动/温启动/热启动慢启动率 (必须包含 startType dimension)",
     ["slowStartRate", "distinctUsers"]),
    ("slowrenderingrate", "slowRenderingRateMetricSet", "慢渲染率",
     "查询应用的慢帧渲染和冻帧率",
     ["slowRenderingRate", "distinctUsers"]),
    ("excessivewakeuprate", "excessiveWakeupRateMetricSet", "过度唤醒率",
     "查询应用的 AlarmManager 过度唤醒率",
     ["excessiveWakeupRate", "distinctUsers"]),
    ("stuckbackgroundwakelockrate", "stuckBackgroundWakelockRateMetricSet", "后台锁定率",
     "查询应用的后台 WakeLock 卡住率",
     ["stuckBgWakelockRate", "distinctUsers"]),
]


# 某些 metric set 有必选 dimensions
_REQUIRED_DIMENSIONS: dict[str, list[str]] = {
    "slowstartrate": ["startType"],
}


def register_reporting_tools(mcp: FastMCP, config: AppConfig) -> None:
    """注册所有 Reporting API tools."""

    # --- apps.search ---
    @mcp.tool(name="googleplay_apps_search")
    def apps_search(page_size: int = 50, page_token: str = "") -> dict:
        """搜索当前 Service Account 可访问的所有 Google Play 应用。

        Args:
            page_size: 每页返回数量, 默认 50
            page_token: 分页 token
        """
        try:
            service = get_reporting_service(config)
            req = service.apps().search(pageSize=page_size, pageToken=page_token or "")
            result = req.execute()
            apps = result.get("apps", [])
            return success(result, f"找到 {len(apps)} 个应用")
        except HttpError as e:
            return handle_google_error(e)

    # --- apps.fetchReleaseFilterOptions ---
    @mcp.tool(name="googleplay_apps_release_filter_options")
    def apps_release_filter_options(package_name: str = "") -> dict:
        """获取应用的 release 版本筛选选项, 用于 vitals 查询时按版本过滤。

        Args:
            package_name: 应用包名 (如 com.example.app), 留空使用默认配置
        """
        pkg = _resolve_package(config, package_name or None)
        if not pkg:
            return error("需要提供 package_name 或设置 GOOGLE_PLAY_PACKAGE_NAME")
        try:
            service = get_reporting_service(config)
            name = f"apps/{pkg}"
            req = service.apps().fetchReleaseFilterOptions(name=name)
            result = req.execute()
            return success(result)
        except HttpError as e:
            return handle_google_error(e)

    # --- vitals 指标查询 (get + query) ---
    for metric_id, resource_id, cn_name, desc, default_metrics in _VITALS_METRIC_SETS:

        def _make_get_tool(mid: str, res_id: str, cn: str):
            @mcp.tool(name=f"googleplay_vitals_{mid}_get")
            def vitals_get(package_name: str = "") -> dict:
                f"""获取 {cn} 指标集的元数据信息 (可用指标和维度)。

                Args:
                    package_name: 应用包名, 留空使用默认配置
                """
                pkg = _resolve_package(config, package_name or None)
                if not pkg:
                    return error("需要提供 package_name 或设置 GOOGLE_PLAY_PACKAGE_NAME")
                try:
                    service = get_reporting_service(config)
                    name = f"apps/{pkg}/{res_id}"
                    resource = getattr(service.vitals(), mid)
                    req = resource().get(name=name)
                    result = req.execute()
                    return success(result)
                except HttpError as e:
                    return handle_google_error(e)
            vitals_get.__doc__ = f"获取 {cn} 指标集的元数据信息 (可用指标和维度)。\n\nArgs:\n    package_name: 应用包名, 留空使用默认配置"
            return vitals_get

        def _make_query_tool(mid: str, res_id: str, cn: str, description: str, def_metrics: list[str]):
            @mcp.tool(name=f"googleplay_vitals_{mid}_query")
            def vitals_query(
                package_name: str = "",
                start_date: str = "",
                end_date: str = "",
                dimensions: list[str] | None = None,
                metrics: list[str] | None = None,
                page_size: int = 1000,
                page_token: str = "",
                aggregation_period: str = "DAILY",
            ) -> dict:
                f"""{description}。

                Args:
                    package_name: 应用包名, 留空使用默认配置
                    start_date: 起始日期, 格式 YYYY-MM-DD (如 2024-01-01)
                    end_date: 结束日期, 格式 YYYY-MM-DD
                    dimensions: 分组维度列表 (如 ["apiLevel", "deviceModel", "countryCode"])
                    metrics: 要查询的指标列表, 留空返回所有指标
                    page_size: 每页行数, 默认 1000, 最大 100000
                    page_token: 分页 token
                    aggregation_period: 聚合周期, DAILY 或 HOURLY
                """
                pkg = _resolve_package(config, package_name or None)
                if not pkg:
                    return error("需要提供 package_name 或设置 GOOGLE_PLAY_PACKAGE_NAME")
                try:
                    service = get_reporting_service(config)
                    name = f"apps/{pkg}/{res_id}"

                    body: dict = {
                        "timelineSpec": {
                            "aggregationPeriod": aggregation_period,
                        },
                        "pageSize": page_size,
                    }

                    if start_date:
                        parts = start_date.split("-")
                        body["timelineSpec"]["startTime"] = {
                            "year": int(parts[0]),
                            "month": int(parts[1]),
                            "day": int(parts[2]),
                        }
                    if end_date:
                        parts = end_date.split("-")
                        body["timelineSpec"]["endTime"] = {
                            "year": int(parts[0]),
                            "month": int(parts[1]),
                            "day": int(parts[2]),
                        }
                    req_dims = _REQUIRED_DIMENSIONS.get(mid, [])
                    body["dimensions"] = dimensions if dimensions else req_dims
                    body["metrics"] = metrics if metrics else def_metrics
                    if page_token:
                        body["pageToken"] = page_token

                    resource = getattr(service.vitals(), mid)
                    req = resource().query(name=name, body=body)
                    result = req.execute()
                    rows = result.get("rows", [])
                    return success(result, f"返回 {len(rows)} 行数据")
                except HttpError as e:
                    return handle_google_error(e)

            vitals_query.__doc__ = f"""{description}。

Args:
    package_name: 应用包名, 留空使用默认配置
    start_date: 起始日期, 格式 YYYY-MM-DD
    end_date: 结束日期, 格式 YYYY-MM-DD
    dimensions: 分组维度列表
    metrics: 要查询的指标列表
    page_size: 每页行数
    page_token: 分页 token
    aggregation_period: 聚合周期 DAILY 或 HOURLY"""
            return vitals_query

        _make_get_tool(metric_id, resource_id, cn_name)
        _make_query_tool(metric_id, resource_id, cn_name, desc, default_metrics)

    # --- vitals.errors.counts ---
    @mcp.tool(name="googleplay_vitals_errors_counts_query")
    def errors_counts_query(
        package_name: str = "",
        start_date: str = "",
        end_date: str = "",
        report_type: str = "CRASH",
        dimensions: list[str] | None = None,
        metrics: list[str] | None = None,
        page_size: int = 1000,
        page_token: str = "",
        aggregation_period: str = "DAILY",
    ) -> dict:
        """查询应用错误计数 (崩溃或 ANR 数量)。

        Args:
            package_name: 应用包名, 留空使用默认配置
            start_date: 起始日期, 格式 YYYY-MM-DD
            end_date: 结束日期, 格式 YYYY-MM-DD
            report_type: 报告类型, CRASH 或 ANR
            dimensions: 分组维度列表
            metrics: 要查询的指标列表
            page_size: 每页行数
            page_token: 分页 token
            aggregation_period: 聚合周期 DAILY 或 HOURLY
        """
        pkg = _resolve_package(config, package_name or None)
        if not pkg:
            return error("需要提供 package_name 或设置 GOOGLE_PLAY_PACKAGE_NAME")
        try:
            service = get_reporting_service(config)
            name = f"apps/{pkg}/errorCountMetricSet"
            body: dict = {
                "timelineSpec": {"aggregationPeriod": aggregation_period},
                "pageSize": page_size,
                "filter": f'reportType = {report_type}',
            }
            if start_date:
                parts = start_date.split("-")
                body["timelineSpec"]["startTime"] = {
                    "year": int(parts[0]), "month": int(parts[1]), "day": int(parts[2]),
                }
            if end_date:
                parts = end_date.split("-")
                body["timelineSpec"]["endTime"] = {
                    "year": int(parts[0]), "month": int(parts[1]), "day": int(parts[2]),
                }
            body["dimensions"] = dimensions if dimensions else ["reportType"]
            body["metrics"] = metrics if metrics else ["errorReportCount", "distinctUsers"]
            if page_token:
                body["pageToken"] = page_token

            req = service.vitals().errors().counts().query(name=name, body=body)
            result = req.execute()
            rows = result.get("rows", [])
            return success(result, f"返回 {len(rows)} 行错误计数数据")
        except HttpError as e:
            return handle_google_error(e)

    # --- vitals.errors.issues ---
    @mcp.tool(name="googleplay_vitals_errors_issues_search")
    def errors_issues_search(
        package_name: str = "",
        filter_expr: str = "",
        page_size: int = 50,
        page_token: str = "",
        interval_start: str = "",
        interval_end: str = "",
    ) -> dict:
        """搜索应用的错误问题 (按根因分组的错误报告)。

        Args:
            package_name: 应用包名, 留空使用默认配置
            filter_expr: 过滤表达式, 如 'reportType = CRASH'
            page_size: 每页数量, 默认 50
            page_token: 分页 token
            interval_start: 时间范围起始, RFC3339 格式 (如 2024-01-01T00:00:00Z)
            interval_end: 时间范围结束, RFC3339 格式
        """
        pkg = _resolve_package(config, package_name or None)
        if not pkg:
            return error("需要提供 package_name 或设置 GOOGLE_PLAY_PACKAGE_NAME")
        try:
            service = get_reporting_service(config)
            parent = f"apps/{pkg}"
            kwargs: dict = {"parent": parent, "pageSize": page_size}
            if filter_expr:
                kwargs["filter"] = filter_expr
            if page_token:
                kwargs["pageToken"] = page_token
            if interval_start and interval_end:
                kwargs["interval.startTime.seconds"] = interval_start
                kwargs["interval.endTime.seconds"] = interval_end

            req = service.vitals().errors().issues().search(**kwargs)
            result = req.execute()
            issues = result.get("errorIssues", [])
            return success(result, f"找到 {len(issues)} 个错误问题")
        except HttpError as e:
            return handle_google_error(e)

    # --- vitals.errors.reports ---
    @mcp.tool(name="googleplay_vitals_errors_reports_search")
    def errors_reports_search(
        package_name: str = "",
        filter_expr: str = "",
        page_size: int = 50,
        page_token: str = "",
        interval_start: str = "",
        interval_end: str = "",
    ) -> dict:
        """搜索应用的详细错误报告 (含堆栈跟踪)。

        Args:
            package_name: 应用包名, 留空使用默认配置
            filter_expr: 过滤表达式, 如 'reportType = CRASH'
            page_size: 每页数量, 默认 50
            page_token: 分页 token
            interval_start: 时间范围起始, RFC3339 格式
            interval_end: 时间范围结束, RFC3339 格式
        """
        pkg = _resolve_package(config, package_name or None)
        if not pkg:
            return error("需要提供 package_name 或设置 GOOGLE_PLAY_PACKAGE_NAME")
        try:
            service = get_reporting_service(config)
            parent = f"apps/{pkg}"
            kwargs: dict = {"parent": parent, "pageSize": page_size}
            if filter_expr:
                kwargs["filter"] = filter_expr
            if page_token:
                kwargs["pageToken"] = page_token
            if interval_start and interval_end:
                kwargs["interval.startTime.seconds"] = interval_start
                kwargs["interval.endTime.seconds"] = interval_end

            req = service.vitals().errors().reports().search(**kwargs)
            result = req.execute()
            reports = result.get("errorReports", [])
            return success(result, f"找到 {len(reports)} 份错误报告")
        except HttpError as e:
            return handle_google_error(e)

    # --- anomalies ---
    @mcp.tool(name="googleplay_anomalies_list")
    def anomalies_list(
        package_name: str = "",
        filter_expr: str = "",
        page_size: int = 50,
        page_token: str = "",
    ) -> dict:
        """列出应用检测到的指标异常 (自动检测超出正常范围的指标值)。

        Args:
            package_name: 应用包名, 留空使用默认配置
            filter_expr: 过滤表达式, 如按时间范围 'activeBetween("2024-01-01","2024-01-31")'
            page_size: 每页数量, 默认 50
            page_token: 分页 token
        """
        pkg = _resolve_package(config, package_name or None)
        if not pkg:
            return error("需要提供 package_name 或设置 GOOGLE_PLAY_PACKAGE_NAME")
        try:
            service = get_reporting_service(config)
            parent = f"apps/{pkg}"
            kwargs: dict = {"parent": parent, "pageSize": page_size}
            if filter_expr:
                kwargs["filter"] = filter_expr
            if page_token:
                kwargs["pageToken"] = page_token

            req = service.anomalies().list(**kwargs)
            result = req.execute()
            anomalies = result.get("anomalies", [])
            return success(result, f"找到 {len(anomalies)} 个异常")
        except HttpError as e:
            return handle_google_error(e)
