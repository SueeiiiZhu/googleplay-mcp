"""Google API 错误处理."""

from __future__ import annotations

import json
import logging

from googleapiclient.errors import HttpError

logger = logging.getLogger(__name__)

_STATUS_HINTS = {
    401: "认证失败，请检查 Service Account 密钥是否正确。",
    403: "权限不足，请确认 Service Account 已被授权访问该应用。",
    404: "资源未找到，请检查 packageName 或其他标识符是否正确。",
    409: "冲突，资源可能已被修改或不处于预期状态。",
    429: "请求过于频繁，请稍后重试。",
}


def format_google_error(err: HttpError) -> str:
    """将 Google API HttpError 格式化为可读文本."""
    status = err.resp.status if err.resp else 0
    hint = _STATUS_HINTS.get(status, "")

    try:
        detail = json.loads(err.content)
        message = detail.get("error", {}).get("message", str(err))
    except (json.JSONDecodeError, AttributeError):
        message = str(err)

    parts = [f"Google API 错误 ({status}): {message}"]
    if hint:
        parts.append(f"提示: {hint}")

    return "\n".join(parts)


def handle_google_error(err: HttpError) -> dict:
    """将 Google API 错误转换为 MCP 错误响应格式."""
    logger.error("Google API error: %s", err)
    text = format_google_error(err)
    return {"content": [{"type": "text", "text": text}], "isError": True}
