# Google Play MCP Server

Google Play 后台数据类 API 的 MCP Server 封装，提供 Vitals 指标、评论、购买验证、订阅管理、财务报告等查询能力。

## 功能

- **Vitals 指标查询**: 崩溃率、ANR 率、慢启动、慢渲染、过度唤醒、后台锁定、低内存杀死
- **错误追踪**: 错误计数、错误问题搜索、错误报告详情 (含堆栈)
- **异常检测**: 自动检测超出正常范围的指标异常
- **用户评论**: 列表、详情、回复
- **购买验证**: 商品购买、订阅购买 (v1/v2)、退款记录
- **商品配置**: 订阅列表、应用内商品列表
- **订单查询**: 订单详情
- **财务报告**: GCS bucket 中的收入/销售/安装等 CSV 报告

## 快速开始

### 安装

```bash
uv sync
```

### 配置

设置环境变量:

```bash
export GOOGLE_SERVICE_ACCOUNT_KEY_FILE=/path/to/service-account.json
export GOOGLE_PLAY_PACKAGE_NAME=com.example.app        # 可选
export GOOGLE_PLAY_REPORT_BUCKET=pubsite_prod_rev_xxx  # 可选
```

或使用 YAML 配置文件 (见 `config.example.yaml`)。

### 运行

**stdio 模式** (默认, 用于 Claude Desktop 等):

```bash
uv run python -m googleplay_mcp
```

**HTTP 模式**:

```bash
uv run python -m googleplay_mcp --transport http --host 127.0.0.1 --port 8000
```

**使用配置文件**:

```bash
uv run python -m googleplay_mcp --config config.yaml
```

### Claude Desktop 配置

在 `claude_desktop_config.json` 中添加:

```json
{
  "mcpServers": {
    "googleplay": {
      "command": "uv",
      "args": ["--directory", "/path/to/googleplay-mcp", "run", "python", "-m", "googleplay_mcp"],
      "env": {
        "GOOGLE_SERVICE_ACCOUNT_KEY_FILE": "/path/to/service-account.json",
        "GOOGLE_PLAY_PACKAGE_NAME": "com.example.app"
      }
    }
  }
}
```

## 前置要求配置指南

### 1. 创建 Google Cloud 项目并启用 API

1. 访问 [Google Cloud Console](https://console.cloud.google.com/)
2. 创建新项目（或选择已有项目）
3. 进入 **API 和服务 → 库**，搜索并启用以下 API：
   - **Google Play Android Developer API** — 评论、购买验证、订阅、订单等
   - **Google Play Developer Reporting API** — Vitals 指标、崩溃率、ANR 等
   - **Cloud Storage API** — （可选）用于下载财务/销售报告

### 2. 创建 Service Account 并下载密钥

1. 在 Google Cloud Console 进入 **IAM 和管理 → 服务账号**
2. 点击 **创建服务账号**
   - 名称：如 `googleplay-mcp`
   - 角色：无需在此处分配（权限在 Play Console 侧授予）
3. 创建完成后，点击该服务账号 → **密钥** 标签页
4. 点击 **添加密钥 → 创建新密钥 → JSON**
5. 下载 JSON 密钥文件，妥善保管（此文件仅生成一次）

### 3. 在 Google Play Console 授予 Service Account 权限

1. 访问 [Google Play Console](https://play.google.com/console/)
2. 进入 **设置 → API 访问权限**
3. 如果是首次设置，需要先 **关联 Google Cloud 项目**：
   - 点击"关联项目"，选择你在步骤 1 创建的 Cloud 项目
4. 在"服务账号"部分，找到刚创建的 Service Account（关联后会自动出现）
5. 点击 **授予访问权限**，根据需求勾选：

| 权限 | 用途 | 需要的 tools |
|------|------|-------------|
| **查看应用信息（只读）** | 基础应用数据 | 所有 tools |
| **查看财务数据、订单和取消订阅调查回复** | 收入、订单 | `orders_get`, `reports_*` |
| **管理订单和订阅** | 购买验证、退款查询 | `purchases_*` |
| **查看应用质量信息（只读）** | Vitals、崩溃、ANR | `vitals_*`, `anomalies_*` |
| **回复评论** | 回复用户评论 | `reviews_reply` |
| **查看评价** | 读取评论 | `reviews_list`, `reviews_get` |

6. 选择权限范围：
   - **所有应用** — 授权访问账号下全部应用
   - **指定应用** — 仅授权访问选定的应用
7. 点击 **邀请用户** 完成授权

> **注意**：权限变更可能需要 **最多 24 小时** 生效。如果刚配置后调用 API 返回 403，请等待后重试。

### 4. （可选）配置 GCS 财务报告 bucket 访问

如需使用 `googleplay_reports_*` tools 下载财务/销售报告：

1. 在 Google Play Console 进入 **下载报告 → 财务**
2. 页面底部找到 **复制 Cloud Storage URI**，格式为：
   ```
   gs://pubsite_prod_rev_01234567890123456789/
   ```
   其中 `pubsite_prod_rev_01234567890123456789` 就是 bucket 名称
3. 前往 [Google Cloud Console → Cloud Storage](https://console.cloud.google.com/storage/browser)
4. 找到该 bucket → **权限** 标签页
5. 点击 **授予访问权限**：
   - 主账号：填入 Service Account 邮箱（如 `googleplay-mcp@your-project.iam.gserviceaccount.com`）
   - 角色：**Storage Object Viewer**（`roles/storage.objectViewer`）
6. 将 bucket 名称配置到环境变量或 config.yaml：
   ```bash
   export GOOGLE_PLAY_REPORT_BUCKET=pubsite_prod_rev_01234567890123456789
   ```

### 5. 验证配置

配置完成后，运行以下命令验证 Service Account 是否能正常工作：

```bash
# 验证密钥文件格式正确
uv run python -c "
import json
with open('/path/to/service-account.json') as f:
    key = json.load(f)
print(f'项目: {key[\"project_id\"]}')
print(f'账号: {key[\"client_email\"]}')
"

# 启动服务器并使用 MCP Inspector 测试
npx @modelcontextprotocol/inspector uv run python -m googleplay_mcp
```

在 MCP Inspector 中调用 `googleplay_apps_search`，如果返回应用列表则说明配置成功。

## 系统服务部署 (HTTP 模式)

以 HTTP 模式部署为系统服务，实现开机自启和自动重启。

### macOS (launchd)

1. 创建配置文件：

```bash
sudo tee /Library/LaunchDaemons/com.googleplay-mcp.plist > /dev/null << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.googleplay-mcp</string>

    <key>ProgramArguments</key>
    <array>
        <string>/Users/xi/.local/bin/uv</string>
        <string>--directory</string>
        <string>/Users/xi/workspace/googleplay-mcp</string>
        <string>run</string>
        <string>python</string>
        <string>-m</string>
        <string>googleplay_mcp</string>
        <string>--transport</string>
        <string>http</string>
        <string>--host</string>
        <string>127.0.0.1</string>
        <string>--port</string>
        <string>8000</string>
    </array>

    <key>EnvironmentVariables</key>
    <dict>
        <key>GOOGLE_SERVICE_ACCOUNT_KEY_FILE</key>
        <string>/path/to/service-account.json</string>
        <key>GOOGLE_PLAY_PACKAGE_NAME</key>
        <string>com.example.app</string>
    </dict>

    <key>RunAtLoad</key>
    <true/>

    <key>KeepAlive</key>
    <true/>

    <key>StandardOutPath</key>
    <string>/var/log/googleplay-mcp.log</string>

    <key>StandardErrorPath</key>
    <string>/var/log/googleplay-mcp.error.log</string>

    <key>WorkingDirectory</key>
    <string>/Users/xi/workspace/googleplay-mcp</string>
</dict>
</plist>
EOF
```

> **注意**：请将 `uv` 路径替换为实际路径，可通过 `which uv` 获取。如果作为当前用户运行（非 root），plist 文件应放在 `~/Library/LaunchAgents/` 下。

2. 管理服务：

```bash
# 加载并启动
sudo launchctl load /Library/LaunchDaemons/com.googleplay-mcp.plist

# 停止并卸载
sudo launchctl unload /Library/LaunchDaemons/com.googleplay-mcp.plist

# 查看状态
sudo launchctl list | grep googleplay-mcp

# 查看日志
tail -f /var/log/googleplay-mcp.log
tail -f /var/log/googleplay-mcp.error.log
```

如果使用 `~/Library/LaunchAgents/` (当前用户级)，则不需要 `sudo`：

```bash
launchctl load ~/Library/LaunchAgents/com.googleplay-mcp.plist
launchctl unload ~/Library/LaunchAgents/com.googleplay-mcp.plist
```

### Linux (systemd)

1. 创建 service 文件：

```bash
sudo tee /etc/systemd/system/googleplay-mcp.service > /dev/null << 'EOF'
[Unit]
Description=Google Play MCP Server
After=network.target

[Service]
Type=simple
User=deploy
Group=deploy
WorkingDirectory=/opt/googleplay-mcp

Environment=GOOGLE_SERVICE_ACCOUNT_KEY_FILE=/opt/googleplay-mcp/service-account.json
Environment=GOOGLE_PLAY_PACKAGE_NAME=com.example.app
# Environment=GOOGLE_PLAY_REPORT_BUCKET=pubsite_prod_rev_xxx

ExecStart=/usr/local/bin/uv --directory /opt/googleplay-mcp run python -m googleplay_mcp --transport http --host 0.0.0.0 --port 8000

Restart=always
RestartSec=5

StandardOutput=journal
StandardError=journal
SyslogIdentifier=googleplay-mcp

[Install]
WantedBy=multi-user.target
EOF
```

> **注意**：请根据实际情况修改 `User`、`WorkingDirectory`、`uv` 路径和环境变量。`--host 0.0.0.0` 表示监听所有网卡，如仅本机访问改为 `127.0.0.1`。

2. 管理服务：

```bash
# 重新加载配置
sudo systemctl daemon-reload

# 启动
sudo systemctl start googleplay-mcp

# 设置开机自启
sudo systemctl enable googleplay-mcp

# 查看状态
sudo systemctl status googleplay-mcp

# 查看日志
sudo journalctl -u googleplay-mcp -f

# 停止
sudo systemctl stop googleplay-mcp

# 禁用开机自启
sudo systemctl disable googleplay-mcp
```

### 使用配置文件启动

两种系统服务都可以改用 `--config` 方式，将运行参数集中到 YAML 文件管理：

```bash
# 将启动命令改为:
uv --directory /path/to/googleplay-mcp run python -m googleplay_mcp --config /path/to/config.yaml
```

这样修改配置只需编辑 YAML 文件并重启服务，无需修改 plist/service 文件。
