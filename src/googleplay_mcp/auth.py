"""Google Service Account 认证."""

from __future__ import annotations

import json
import logging
from typing import TYPE_CHECKING

from google.oauth2 import service_account
from googleapiclient.discovery import build

if TYPE_CHECKING:
    from googleplay_mcp.config import AppConfig

logger = logging.getLogger(__name__)

SCOPES = [
    "https://www.googleapis.com/auth/androidpublisher",
    "https://www.googleapis.com/auth/playdeveloperreporting",
    "https://www.googleapis.com/auth/devstorage.read_only",
]

_credentials: service_account.Credentials | None = None
_publisher_client = None
_reporting_service = None


def get_credentials(config: AppConfig) -> service_account.Credentials:
    """获取或创建 Google Service Account 凭据."""
    global _credentials
    if _credentials is not None:
        return _credentials

    key_file = config.google.service_account_key_file
    key_json = config.google.service_account_key

    if key_file:
        logger.info("使用 service account key file: %s", key_file)
        _credentials = service_account.Credentials.from_service_account_file(
            key_file, scopes=SCOPES
        )
    elif key_json:
        logger.info("使用 inline service account key")
        info = json.loads(key_json)
        _credentials = service_account.Credentials.from_service_account_info(
            info, scopes=SCOPES
        )
    else:
        raise RuntimeError(
            "未配置 Google 认证。请设置 GOOGLE_SERVICE_ACCOUNT_KEY_FILE 或 GOOGLE_SERVICE_ACCOUNT_KEY"
        )

    return _credentials


def get_publisher_client(config: AppConfig):
    """获取 androidpublisher v3 API client."""
    global _publisher_client
    if _publisher_client is not None:
        return _publisher_client

    credentials = get_credentials(config)
    _publisher_client = build("androidpublisher", "v3", credentials=credentials)
    return _publisher_client


def get_reporting_service(config: AppConfig):
    """获取 playdeveloperreporting v1beta1 API client."""
    global _reporting_service
    if _reporting_service is not None:
        return _reporting_service

    credentials = get_credentials(config)
    _reporting_service = build(
        "playdeveloperreporting", "v1beta1", credentials=credentials
    )
    return _reporting_service


def reset_clients() -> None:
    """重置所有缓存的客户端 (用于测试)."""
    global _credentials, _publisher_client, _reporting_service
    _credentials = None
    _publisher_client = None
    _reporting_service = None
