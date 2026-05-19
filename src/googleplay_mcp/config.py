"""配置加载: CLI args > config.yaml > env vars > defaults."""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml


@dataclass
class ServerConfig:
    transport: str = "stdio"
    host: str = "127.0.0.1"
    port: int = 8000


@dataclass
class GoogleConfig:
    service_account_key_file: str | None = None
    service_account_key: str | None = None
    default_package_name: str | None = None
    report_bucket: str | None = None
    gsutil_bin: str | None = None


@dataclass
class AppConfig:
    server: ServerConfig = field(default_factory=ServerConfig)
    google: GoogleConfig = field(default_factory=GoogleConfig)


def _load_yaml(path: str | Path) -> dict:
    with open(path) as f:
        return yaml.safe_load(f) or {}


def _apply_env(config: AppConfig) -> None:
    """用环境变量填充未设置的字段."""
    if not config.google.service_account_key_file:
        config.google.service_account_key_file = os.getenv("GOOGLE_SERVICE_ACCOUNT_KEY_FILE")
    if not config.google.service_account_key:
        config.google.service_account_key = os.getenv("GOOGLE_SERVICE_ACCOUNT_KEY")
    if not config.google.default_package_name:
        config.google.default_package_name = os.getenv("GOOGLE_PLAY_PACKAGE_NAME")
    if not config.google.report_bucket:
        config.google.report_bucket = os.getenv("GOOGLE_PLAY_REPORT_BUCKET")
    if not config.google.gsutil_bin:
        config.google.gsutil_bin = os.getenv("GOOGLE_PLAY_GSUTIL_BIN")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Google Play MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        help="Transport mode (default: stdio)",
    )
    parser.add_argument("--host", help="HTTP host (default: 127.0.0.1)")
    parser.add_argument("--port", type=int, help="HTTP port (default: 8000)")
    parser.add_argument("--config", help="Path to YAML config file")
    return parser


def load_config(args: argparse.Namespace | None = None) -> AppConfig:
    """加载配置, 优先级: CLI > YAML > ENV > defaults."""
    config = AppConfig()

    # Layer 1: YAML config file
    config_path = getattr(args, "config", None) if args else None
    if config_path and Path(config_path).exists():
        data = _load_yaml(config_path)
        server_data = data.get("server", {})
        google_data = data.get("google", {})

        if "transport" in server_data:
            config.server.transport = server_data["transport"]
        if "host" in server_data:
            config.server.host = server_data["host"]
        if "port" in server_data:
            config.server.port = server_data["port"]

        if "service_account_key_file" in google_data:
            config.google.service_account_key_file = google_data["service_account_key_file"]
        if "default_package_name" in google_data:
            config.google.default_package_name = google_data["default_package_name"]
        if "report_bucket" in google_data:
            config.google.report_bucket = google_data["report_bucket"]
        if "gsutil_bin" in google_data:
            config.google.gsutil_bin = google_data["gsutil_bin"]

    # Layer 2: Environment variables (fill gaps)
    _apply_env(config)

    # Layer 3: CLI args override everything
    if args:
        if args.transport:
            config.server.transport = args.transport
        if args.host:
            config.server.host = args.host
        if args.port:
            config.server.port = args.port

    return config
