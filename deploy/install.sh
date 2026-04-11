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

install_macos() {
    check_uv

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

    # 生成 plist, 替换占位符
    sed \
        -e "s|/usr/local/bin/uv|${uv_path}|g" \
        -e "s|/path/to/googleplay-mcp|${PROJECT_DIR}|g" \
        "${SCRIPT_DIR}/${PLIST_NAME}" > "${dest}"

    log "已写入 ${dest}"
    log ""
    log "接下来请手动完成:"
    log "  1. 编辑 ${dest} 中的环境变量 (Service Account 路径、包名等)"
    log "  2. 加载服务:"
    if $system_mode; then
        log "     sudo launchctl load ${dest}"
        log "  3. 查看状态: sudo launchctl list | grep googleplay-mcp"
        log "  4. 查看日志: tail -f /var/log/googleplay-mcp.log"
    else
        log "     launchctl load ${dest}"
        log "  3. 查看状态: launchctl list | grep googleplay-mcp"
        log "  4. 查看日志: tail -f /var/log/googleplay-mcp.log"
    fi
}

install_linux() {
    check_uv
    [[ $EUID -ne 0 ]] && err "Linux 安装需要 sudo"

    local uv_path
    uv_path="$(which uv)"
    local dest="/etc/systemd/system/${SERVICE_NAME}"

    # 生成 service 文件, 替换 uv 路径和项目路径
    sed \
        -e "s|/usr/local/bin/uv|${uv_path}|g" \
        -e "s|/opt/googleplay-mcp|${PROJECT_DIR}|g" \
        "${SCRIPT_DIR}/${SERVICE_NAME}" > "${dest}"

    systemctl daemon-reload

    log "已写入 ${dest}"
    log ""
    log "接下来请手动完成:"
    log "  1. 编辑 ${dest} 中的 User/Group 和环境变量"
    log "  2. 启动服务:     sudo systemctl start googleplay-mcp"
    log "  3. 设置开机自启: sudo systemctl enable googleplay-mcp"
    log "  4. 查看状态:     sudo systemctl status googleplay-mcp"
    log "  5. 查看日志:     sudo journalctl -u googleplay-mcp -f"
}

uninstall() {
    log "卸载 Google Play MCP 服务..."

    # macOS
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

    # Linux
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
