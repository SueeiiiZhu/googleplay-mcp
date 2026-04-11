#!/usr/bin/env bash
#
# Google Play MCP Server 部署安装脚本
# 用法:
#   macOS (当前用户): ./install.sh macos
#   macOS (系统级):   sudo ./install.sh macos --system
#   Linux:            sudo ./install.sh linux
#   卸载:             [sudo] ./install.sh uninstall
#

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
PLIST_NAME="com.googleplay-mcp.plist"
SERVICE_NAME="googleplay-mcp.service"

log() { echo "==> $*"; }
err() { echo "ERROR: $*" >&2; exit 1; }

check_uv() {
    if ! command -v uv &>/dev/null; then
        err "未找到 uv, 请先安装: https://docs.astral.sh/uv/getting-started/installation/"
    fi
    log "uv 路径: $(which uv)"
}

ensure_config() {
    local config_path="${PROJECT_DIR}/config.yaml"
    if [[ ! -f "$config_path" ]]; then
        cp "${PROJECT_DIR}/config.example.yaml" "$config_path"
        log "已从 config.example.yaml 创建 config.yaml, 请编辑其中的配置"
    fi
}

install_macos() {
    check_uv
    ensure_config

    local system_mode=false
    [[ "${1:-}" == "--system" ]] && system_mode=true

    local uv_path
    uv_path="$(which uv)"

    if $system_mode; then
        local dest="/Library/LaunchDaemons/${PLIST_NAME}"
        log "安装系统级服务到 ${dest}"
        [[ $EUID -ne 0 ]] && err "系统级安装需要 sudo"
    else
        local dest="${HOME}/Library/LaunchAgents/${PLIST_NAME}"
        mkdir -p "${HOME}/Library/LaunchAgents"
        log "安装用户级服务到 ${dest}"
    fi

    sed \
        -e "s|/usr/local/bin/uv|${uv_path}|g" \
        -e "s|/path/to/googleplay-mcp|${PROJECT_DIR}|g" \
        "${SCRIPT_DIR}/${PLIST_NAME}" > "${dest}"

    log "已写入 ${dest}"
    log ""
    log "接下来:"
    log "  1. 编辑 ${PROJECT_DIR}/config.yaml 填写 Service Account 路径、包名等"
    log "  2. 加载服务:"
    if $system_mode; then
        log "     sudo launchctl load ${dest}"
    else
        log "     launchctl load ${dest}"
    fi
}

install_linux() {
    check_uv
    ensure_config
    [[ $EUID -ne 0 ]] && err "Linux 安装需要 sudo"

    local uv_path
    uv_path="$(which uv)"
    local dest="/etc/systemd/system/${SERVICE_NAME}"

    sed \
        -e "s|/usr/local/bin/uv|${uv_path}|g" \
        -e "s|/opt/googleplay-mcp|${PROJECT_DIR}|g" \
        "${SCRIPT_DIR}/${SERVICE_NAME}" > "${dest}"

    systemctl daemon-reload

    log "已写入 ${dest}"
    log ""
    log "接下来:"
    log "  1. 编辑 ${PROJECT_DIR}/config.yaml 填写 Service Account 路径、包名等"
    log "  2. 如需修改运行用户, 编辑 ${dest} 中的 User/Group"
    log "  3. 启动: sudo systemctl start googleplay-mcp"
    log "  4. 开机自启: sudo systemctl enable googleplay-mcp"
}

uninstall() {
    log "卸载 Google Play MCP 服务..."

    local plist_user="${HOME}/Library/LaunchAgents/${PLIST_NAME}"
    local plist_system="/Library/LaunchDaemons/${PLIST_NAME}"

    if [[ -f "$plist_user" ]]; then
        launchctl unload "$plist_user" 2>/dev/null || true
        rm -f "$plist_user"
        log "已移除 ${plist_user}"
    fi
    if [[ -f "$plist_system" ]]; then
        sudo launchctl unload "$plist_system" 2>/dev/null || true
        sudo rm -f "$plist_system"
        log "已移除 ${plist_system}"
    fi

    local service_path="/etc/systemd/system/${SERVICE_NAME}"
    if [[ -f "$service_path" ]]; then
        sudo systemctl stop googleplay-mcp 2>/dev/null || true
        sudo systemctl disable googleplay-mcp 2>/dev/null || true
        sudo rm -f "$service_path"
        sudo systemctl daemon-reload
        log "已移除 ${service_path}"
    fi

    log "卸载完成"
}

case "${1:-}" in
    macos)  install_macos "${2:-}" ;;
    linux)  install_linux ;;
    uninstall) uninstall ;;
    *)
        echo "用法:"
        echo "  macOS (当前用户): $0 macos"
        echo "  macOS (系统级):   sudo $0 macos --system"
        echo "  Linux:            sudo $0 linux"
        echo "  卸载:             $0 uninstall"
        exit 1
        ;;
esac
