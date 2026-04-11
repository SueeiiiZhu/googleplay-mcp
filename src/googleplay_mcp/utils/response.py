"""响应格式化工具."""

from __future__ import annotations

import json
from typing import Any


def success(data: Any, summary: str | None = None) -> dict:
    """格式化成功的 MCP 响应."""
    parts = []
    if summary:
        parts.append(summary)
    parts.append(json.dumps(data, indent=2, ensure_ascii=False, default=str))
    return {"content": [{"type": "text", "text": "\n".join(parts)}]}


def error(message: str) -> dict:
    """格式化错误的 MCP 响应."""
    return {"content": [{"type": "text", "text": message}], "isError": True}
