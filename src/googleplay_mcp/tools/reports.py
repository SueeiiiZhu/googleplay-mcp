"""GCS 财务/销售报告下载 tools。

优先用 Service Account 走 google-cloud-storage SDK。当 SA 在 GCS bucket 上
没有 object 读权限（403 Forbidden）时，自动 fallback 到本机 gsutil（沿用
gcloud auth login 的用户凭证），用于绕开 Play Console → GCS IAM 同步问题。

财务报告通常是 .zip 包，内含 utf-16 编码的 CSV，本模块会自动解压并解析。
"""

from __future__ import annotations

import csv
import datetime as _dt
import io
import logging
import os
import re
import subprocess
import zipfile
from pathlib import Path
from typing import TYPE_CHECKING

from googleplay_mcp.auth import get_credentials
from googleplay_mcp.utils.response import error, success

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

    from googleplay_mcp.config import AppConfig


logger = logging.getLogger(__name__)

TYPE_PREFIX_MAP = {
    "earnings": "earnings/",
    "sales": "sales/",
    "installs": "stats/installs/",
    "crashes": "stats/crashes/",
    "reviews": "reviews/",
}

GSUTIL_TIMEOUT = 300


def _resolve_gsutil_bin(config: AppConfig) -> str:
    return config.google.gsutil_bin or os.getenv("GOOGLE_PLAY_GSUTIL_BIN") or "gsutil"


def _resolve_local_dir(config: AppConfig) -> Path | None:
    raw = config.google.report_local_dir
    if not raw:
        return None
    p = Path(raw).expanduser()
    if not p.is_dir():
        logger.warning("report_local_dir=%s 不存在或不是目录, 跳过本地优先", p)
        return None
    return p.resolve()


def _safe_local_path(local_dir: Path, file_path: str) -> Path | None:
    """拼出本地路径并防止路径穿越 (..)。"""
    candidate = (local_dir / file_path).resolve()
    try:
        candidate.relative_to(local_dir)
    except ValueError:
        logger.warning("file_path=%s 解析后逃逸出 local_dir, 拒绝", file_path)
        return None
    return candidate


def _list_local_files(
    local_dir: Path, full_prefix: str, max_results: int
) -> list[dict]:
    """扫描 local_dir 下匹配 full_prefix 的文件 (镜像 GCS 路径)。"""
    if "/" in full_prefix:
        dir_part, _, name_prefix = full_prefix.rpartition("/")
    else:
        dir_part, name_prefix = "", full_prefix

    scan_root = local_dir / dir_part if dir_part else local_dir
    if not scan_root.is_dir():
        return []

    files: list[dict] = []
    for entry in sorted(scan_root.iterdir()):
        if not entry.is_file():
            continue
        if name_prefix and not entry.name.startswith(name_prefix):
            continue
        stat = entry.stat()
        rel_name = entry.relative_to(local_dir).as_posix()
        files.append(
            {
                "name": rel_name,
                "size": stat.st_size,
                "updated": _dt.datetime.fromtimestamp(
                    stat.st_mtime, tz=_dt.timezone.utc
                ).isoformat(),
            }
        )
        if len(files) >= max_results:
            break
    return files


def _is_forbidden(exc: Exception) -> bool:
    try:
        from google.api_core.exceptions import Forbidden

        if isinstance(exc, Forbidden):
            return True
    except ImportError:
        pass
    msg = str(exc)
    return "403" in msg and ("storage.objects" in msg or "Forbidden" in msg)


def _gsutil_list(
    bucket: str, full_prefix: str, max_results: int, gsutil_bin: str
) -> list[dict]:
    target = f"gs://{bucket}/{full_prefix}*"
    cmd = [gsutil_bin, "ls", "-l", target]
    try:
        out = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=GSUTIL_TIMEOUT,
            check=True,
        )
    except FileNotFoundError as e:
        raise RuntimeError(
            f"找不到 {gsutil_bin}，请确认服务器已安装 gsutil 并在 PATH 中，"
            "或通过 google.gsutil_bin (yaml) / GOOGLE_PLAY_GSUTIL_BIN (env) 指定绝对路径"
        ) from e
    except subprocess.CalledProcessError as e:
        err_msg = (e.stderr or e.stdout or "").strip()
        raise RuntimeError(f"gsutil ls 失败 (exit={e.returncode}): {err_msg}") from e

    line_re = re.compile(r"^\s*(\d+)\s+(\S+)\s+(gs://\S+)\s*$")
    bucket_prefix = f"gs://{bucket}/"
    files: list[dict] = []
    for line in out.stdout.splitlines():
        if not line.strip() or line.startswith("TOTAL:"):
            continue
        m = line_re.match(line)
        if not m:
            continue
        uri = m.group(3)
        name = uri[len(bucket_prefix):] if uri.startswith(bucket_prefix) else uri
        files.append({"name": name, "size": int(m.group(1)), "updated": m.group(2)})
        if len(files) >= max_results:
            break
    return files


def _gsutil_download_bytes(bucket: str, file_path: str, gsutil_bin: str) -> bytes:
    target = f"gs://{bucket}/{file_path}"
    cmd = [gsutil_bin, "cp", target, "-"]
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            timeout=GSUTIL_TIMEOUT,
            check=True,
        )
    except FileNotFoundError as e:
        raise RuntimeError(
            f"找不到 {gsutil_bin}，请确认服务器已安装 gsutil 并在 PATH 中"
        ) from e
    except subprocess.CalledProcessError as e:
        err_msg = e.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"gsutil cp 失败 (exit={e.returncode}): {err_msg}") from e
    return proc.stdout


def _decode_csv_bytes(data: bytes) -> str:
    for encoding in ("utf-16", "utf-8-sig", "utf-8"):
        try:
            return data.decode(encoding)
        except UnicodeDecodeError:
            continue
    return data.decode("utf-8", errors="replace")


def _parse_csv_text(text: str, max_rows: int) -> dict:
    reader = csv.DictReader(io.StringIO(text))
    rows: list[dict] = []
    for i, row in enumerate(reader):
        if i >= max_rows:
            break
        rows.append(dict(row))
    return {
        "headers": list(reader.fieldnames or []),
        "rows": rows,
        "row_count": len(rows),
        "truncated": len(rows) >= max_rows,
    }


def _parse_report_bytes(data: bytes, file_path: str, max_rows: int) -> dict:
    if file_path.lower().endswith(".zip"):
        with zipfile.ZipFile(io.BytesIO(data)) as zf:
            csv_members = [n for n in zf.namelist() if n.lower().endswith(".csv")]
            if not csv_members:
                return {
                    "headers": [],
                    "rows": [],
                    "row_count": 0,
                    "zip_members": zf.namelist(),
                    "note": "zip 内未找到 CSV 文件",
                }
            if len(csv_members) == 1:
                text = _decode_csv_bytes(zf.read(csv_members[0]))
                result = _parse_csv_text(text, max_rows)
                result["source_file"] = csv_members[0]
                return result
            members_result = []
            for name in csv_members:
                text = _decode_csv_bytes(zf.read(name))
                members_result.append({"name": name, **_parse_csv_text(text, max_rows)})
            return {"csv_files": members_result, "file_count": len(members_result)}
    return _parse_csv_text(_decode_csv_bytes(data), max_rows)


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
        full_prefix = TYPE_PREFIX_MAP.get(report_type, f"{report_type}/")
        if prefix:
            full_prefix += prefix

        local_dir = _resolve_local_dir(config)
        if local_dir is not None:
            files = _list_local_files(local_dir, full_prefix, max_results)
            if files:
                return success(
                    files, f"找到 {len(files)} 个报告文件 [from local]"
                )
            logger.info("本地无 %s* 匹配, fallback 到 GCS", full_prefix)

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
            blobs = list(bucket_obj.list_blobs(prefix=full_prefix, max_results=max_results))
            files = [
                {"name": b.name, "size": b.size, "updated": str(b.updated)}
                for b in blobs
            ]
            return success(files, f"找到 {len(files)} 个报告文件")
        except Exception as e:
            if _is_forbidden(e):
                logger.warning("SA list 返回 403, fallback 到 gsutil: %s", e)
                try:
                    files = _gsutil_list(
                        bucket_name,
                        full_prefix,
                        max_results,
                        _resolve_gsutil_bin(config),
                    )
                    return success(
                        files,
                        f"找到 {len(files)} 个报告文件 (via gsutil fallback)",
                    )
                except Exception as e2:
                    return error(f"SA 403 且 gsutil fallback 失败: {e2}")
            return error(f"列出报告文件失败: {e}")

    @mcp.tool(name="googleplay_reports_download")
    def reports_download(
        file_path: str,
        bucket: str = "",
        max_rows: int = 500,
    ) -> dict:
        """下载并解析 Google Play 报告文件 (CSV 直接解析, .zip 自动解压)。

        Args:
            file_path: 报告文件路径 (从 reports_list_files 获取的 name 字段)
            bucket: GCS bucket 名称, 留空使用默认配置
            max_rows: 最大返回行数, 默认 500 (防止超大文件)
        """
        used_gsutil = False
        used_local = False
        data: bytes | None = None

        local_dir = _resolve_local_dir(config)
        if local_dir is not None:
            local_path = _safe_local_path(local_dir, file_path)
            if local_path is not None and local_path.is_file():
                data = local_path.read_bytes()
                used_local = True
            else:
                logger.info("本地无 %s, fallback 到 GCS", file_path)

        if data is None:
            bucket_name = bucket or config.google.report_bucket
            if not bucket_name:
                return error("需要提供 bucket 名称或设置 GOOGLE_PLAY_REPORT_BUCKET")
            try:
                from google.cloud import storage

                credentials = get_credentials(config)
                client = storage.Client(credentials=credentials, project=credentials.project_id)
                bucket_obj = client.bucket(bucket_name)
                blob = bucket_obj.blob(file_path)
                data = blob.download_as_bytes()
            except Exception as e:
                if _is_forbidden(e):
                    logger.warning("SA download 返回 403, fallback 到 gsutil: %s", e)
                    try:
                        data = _gsutil_download_bytes(
                            bucket_name, file_path, _resolve_gsutil_bin(config)
                        )
                        used_gsutil = True
                    except Exception as e2:
                        return error(f"SA 403 且 gsutil fallback 失败: {e2}")
                else:
                    return error(f"下载报告失败: {e}")

        try:
            parsed = _parse_report_bytes(data, file_path, max_rows)
        except Exception as e:
            return error(f"解析报告失败 ({file_path}): {e}")

        if "csv_files" in parsed:
            total_rows = sum(m["row_count"] for m in parsed["csv_files"])
            summary = (
                f"解析 {file_path} 得到 {parsed['file_count']} 个 CSV 共 {total_rows} 行"
            )
        else:
            row_count = parsed.get("row_count", 0)
            summary = f"解析 {file_path} 得到 {row_count} 行数据"
            if parsed.get("truncated"):
                summary += f" (前 {max_rows} 行, 已截断)"

        if used_local:
            summary += " [from local]"
        elif used_gsutil:
            summary += " [via gsutil fallback]"
        return success(parsed, summary)
